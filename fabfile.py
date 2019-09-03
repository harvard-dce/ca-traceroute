
import os
import json
import socket
from bs4 import BeautifulSoup
from fabric import task, Connection, SerialGroup as Group
from invoke.exceptions import Exit
from iperf3 import TestResult



@task
def init_check(c):
    if not os.path.isdir('output'):
        os.mkdir('output')

    if not os.path.exists('ca-hosts.json'):
        raise Exit("missing ca-hosts.json file. did you run 'generate-ca-hosts'?")

@task
def generate_ca_hosts(c, html_file):
    with open(html_file, 'r') as f:
        html = f.read()

    soup = BeautifulSoup(html, "lxml")
    ca_links = soup.find_all('span', class_="text-primary")
    ca_names = [x.text.strip() for x in ca_links]
    ca_hosts = [x + ".dce.harvard.edu" for x in ca_names]

    with open('ca-hosts.json', 'w') as f:
        json.dump(ca_hosts, f, indent=2)


@task(pre=[init_check])
def install_iperf3(c, ca_host=None, force=False):

    ca_host_group = get_ca_host_group(ca_host)

    for conn in ca_host_group:
        print("Working on {}".format(conn.host))
        try:

            exists = conn.run("ls /usr/bin/iperf3", warn=True, hide=True).ok
            if exists and not force:
                print("already installed!")
                continue

            conn.run("curl -s -o /usr/lib64/libiperf.so.0 https://iperf.fr/download/ubuntu/libiperf.so.0_3.1.3")
            conn.run("curl -s -o /usr/bin/iperf3 https://iperf.fr/download/ubuntu/iperf3_3.1.3")
            conn.run("chmod 0755 /usr/bin/iperf3")
            conn.run("iperf3 -v")
        except socket.timeout:
            print("Connection timed out after 5s to {}".format(conn.host))
        except socket.gaierror as e:
            print("Error installing iperf3 on {}: {}".format(conn.host, str(e)))


@task(pre=[init_check])
def iperf3(c, dest_host, ca_host=None, parallel=None, stdout=False):

    server_pid = None

    try:
        # 1. get conn to admin
        dest_conn = Connection(dest_host, connect_timeout=5)

        # 2. run iperf3 in daemon mode & save pid
        dest_conn.sudo("iperf3 -s -D")
        server_pid = dest_conn.run("pidof -s iperf3", hide=True).stdout

        ca_host_group = get_ca_host_group(ca_host)

        if parallel is not None:
            parallel = "-P {}".format(int(parallel))

        cmd = "iperf3 -J -c {} {}".format(dest_host, parallel)

        for conn in ca_host_group:
            print("Working on {}".format(conn.host))
            try:
                result = conn.run(cmd, pty=True, hide=True, warn=True).stdout
            except socket.timeout:
                print("Connection timed out after 5s to {}".format(conn.host))
                continue
            except socket.gaierror as e:
                print(str(e))
                continue

            tr = TestResult(result)
            ca = conn.host.split('.')[0]

            cw_cmd = ("aws --profile test cloudwatch put-metric-data --region us-east-1 "
                      "--namespace 'Capture Agents' --dimensions CaptureAgent={} "
                      "--metric-name Sent_Mbps --value {} --unit 'Megabits/Second'") \
                .format(ca, tr.sent_Mbps)

            conn.local(cw_cmd)

    finally:
        if server_pid is not None:
            print("Stopping iperf3 server")
            dest_conn.sudo("kill {}".format(server_pid))


@task
def clean(c):
    if os.path.isdir('output'):
        c.run("rm -rf output")


@task(pre=[init_check])
def traceroutes(c, destination, ca_host=None, port=None, runs=3):

    for idx in range(1, int(runs) + 1):
        ca_host_group = get_ca_host_group(ca_host)
        for conn in ca_host_group:
            gen_traceroute(conn, destination, port, idx)


def gen_traceroute(conn, destination, port, run_idx):
    print("Working on {}".format(conn.host))

    if port is not None:
        port = "-p {}".format(port)
    else:
        port = ""

    outfile = "output/{}.txt".format(conn.host)
    cmd = "traceroute {} {}".format(port, destination)

    try:
        result = conn.run(cmd, pty=True).stdout
    except socket.timeout:
        result = "Connection timed out after 5s to {}".format(conn.host)
    except socket.gaierror as e:
        result = str(e)

    with open(outfile, 'a') as f:
        f.write("Run #{}\n\n".format(run_idx))
        f.write(result)
        f.write("\n\n")

def get_ca_host_group(ca_host=None):

    with open('ca-hosts.json', 'r') as f:
        ca_hosts = json.load(f)

    if ca_host is not None:
        ca_hosts = [x for x in ca_hosts if x.startswith(ca_host)]

    return Group(*ca_hosts, user='root', connect_timeout=5)

