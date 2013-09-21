redfrog-scraper
===============

Scripts that scrape the Red Frog queue status and generate some graphs.

Background
----------

These scripts scrape the queue status of [Red Frog][1], an Eve Online freight-handling corporation,
and do various things with the data extracted.

The results are stored in a local sqlite database.
Graphs showing the current queue status and historical queue handling times are generated.
Finally, the graphs are uploaded to a public Amazon S3 bucket for display.

A wrapper script coordinates the scraping/generation/upload steps and periodically refreshes them when the
queue status updates.

It's all a bit of a horrible hack but seems to do the job.
This code currently runs on an EC2 instance and [uploads the graphs here][3]

Prerequisites
-------------

 * Python 2.7
 * python-boto
 * A character that belongs to Red Frog Freight for authentication
 * An Amazon S3 bucket that you have permissions to upload to

Setup
-----

The DB filename is currently hardcoded to 'redfrog.db'.

Other configuration is entirely via environment variables:

 * EVE_CHARID: the character ID to use when authenticating to the Red Frog website; required.
 * EVE_CHARNAME: the character name to use when authenticating to the Red Frog website; required.
 * EVE_CORPID: the corporation ID for authentication; optional; defaults to the Red Frog Freight corporation ID
 * EVE_CORPNAME: the corporation name for authentication; optional; defaults to 'Red Frog Freight'
 * EVE_ALLIANCEID: the alliance ID for authentication; optional; defaults to the Red-Frog alliance ID
 * EVE_ALLIANCENAME: the alliance name for authentication; optional; defaults to 'Red-Frog'
 * EVE_SERVERIP: the server IP to present to the webserver; optional; defaults to 87.237.38.200:26000, the Tranquillity server IP at the time of writing.
 * S3_BUCKET: the S3 bucket name to upload to; optional; defaults to frog.randomly.org.

Additionally, you will need to provide S3 authentication info in a form accepted by boto (see [this article][2] for more details).
If you happen to be running on an EC2 instance with an IAM role configured, boto should magically autodiscover that.

Running
-------

updater.py is the main entry point.

scrape_ncf.py and scrape_tracker.py can be run directly, given a filename, to parse and display the results of scraping. This is useful for
diagnosing parse problems.

queue.py, when run directly, will show the current queue status according to the local database state.

graph.py, when run directly, will regenerate the current set of graphs according to the local database state.

Logging
-------

updater.py writes logs to stdout/stderr. You probably want to capture these.

It also writes the following files:

 * log/ncf-latest.html: a copy of the last downloaded copy of the nearest contract finder page
 * log/tracker-latest.html: a copy of the last downloaded copy of the contract tracker page
 * log/ncf-missing-TIMESTAMP.html: a copy of any downloaded NCF page where the number of parsed contracts does not match the claimed number of contracts in the queue; useful for after-the-fact diagnosing of parse problems.
 * log/tracker-missing-TIMESTAMP.html: a copy of any downloaded contract tracker page where the number of parsed contracts does not match the claimed number of pending contracts; useful for after-the-fact diagnosing of parse problems.
 * graph/*.png: timestamped copies of the graphs as they are generated.

[1]: http://red-frog.org/                           "Red Frog Freight"
[2]: https://aws.amazon.com/articles/Amazon-S3/3998 "Getting Started with AWS and Python"
[3]: http://frog.randomly.org/                      "Red Frog queue status graphs"
