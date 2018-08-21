
import os
import json
import socket
from bs4 import BeautifulSoup
from fabric import task, SerialGroup as Group
from invoke.exceptions import Exit


@task
def generate_host_list(c, html_file):
    with open(html_file, 'r') as f:
        html = f.read()

    soup = BeautifulSoup(html, "lxml")
    ca_links = soup.find_all('a', role="button", target="_blank")
    hrefs = [x.attrs['href'] for x in ca_links]
    hosts = [x.split('://')[1].replace('/', '') for x in hrefs]

    with open('hosts.json', 'w') as f:
        json.dump(hosts, f, indent=2)


@task
def clean(c):
    if os.path.isdir('output'):
        c.run("rm -rf output")


@task
def traceroutes(c, destination, port=None, runs=3):
    if not os.path.exists('hosts.json'):
        raise Exit("missing hosts.json file. did you run 'generate-host-list'?")
    with open('hosts.json', 'r') as f:
        hosts = json.load(f)

    if not os.path.isdir('output'):
        os.mkdir('output')

    for idx in range(1, int(runs) + 1):
        host_group = Group(*hosts, user='root', connect_timeout=5)
        for host in host_group:
            gen_traceroute(host, destination, port, idx)


def gen_traceroute(c, destination, port, run_idx):
    print("Working on {}".format(c.host))

    if port is not None:
        port = "-p {}".format(port)
    else:
        port = ""

    outfile = "output/{}.txt".format(c.host)
    cmd = "traceroute {} {}".format(port, destination)

    try:
        result = c.run(cmd, pty=True).stdout
    except socket.timeout:
        result = "Connection timed out after 5s to {}".format(c.host)
    except socket.gaierror as e:
        result = str(e)

    with open(outfile, 'a') as f:
        f.write("Run #{}\n\n".format(run_idx))
        f.write(result)
        f.write("\n\n")









