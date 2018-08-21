
# ca-traceroute

A fabric script to gather traceroute information from our network of capture agents.

### Setup

* Python 3.x
* `pip install -r requirements.txt`
* `DCE_Epiphan` private key loaded into your ssh agent via `ssh-add [path to key file]`

Run `fab -l` to confirm installation and view the list of fabric tasks.

### Generate the capture agent hosts list

1. visit https://catracker.dcex.harvard.edu/ in your browser
1. Right-click, view the html source, and save as "Webpage, HTML Only" to a file, e.g. `catracker.html`
1. Run `fab generate-host-list catracker.html`

You should now have a `hosts.json` file in the project directory. `cat` the file
to confirm it contains a list of the capture agent hostnames.

### Run the traceroutes

The traceroute task will cycle through the list of capture agent hosts and execute
a remote `traceroute` command on each host, capturing the output in a collection of
.txt files in a local `output` directory. The task command is:

`fab traceroutes --destination [admin host]`

The `[admin host]` value can be a hostname or ip address. If it's a hostname the
traceroute process will also involve dns resolution at each step, so probably best
to use the IP address (?).

The task takes an optional `--runs` argument for specifying the number of traceroute
commands results to collect. The default is 3 runs per host.

You can also specify a `--port` value, e.g. `--port 8080` but I think this would
only be useful in trying to determine if a particular port was blocked somewhere
along the route.

**Note**: The process takes quite a long time, e.g. my initial run took ~5 hours.

### Cleanup

The `traceroute` task appends the output to the files in `output`. Run `fab clean`
between runs to wipe the existing `output` and start clean.

