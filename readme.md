
<!-- -*- markdown -*- -->

# Bugs.txt

## About

Bugs.txt is a distributed bug tracker. It stores the bugs as text
files inside the buggy source tree. There is no need for an install on
a server somewhere. The bugs themselves are stored inside text files
(to make it easier to solve versioning conflicts). Bugs.txt includes a
web UI for handling the bugs.

## License

Bugs.txt is licensed under the 2-clause BSD license (see the
`license.txt` file).

## Warning

Bugs.txt is very unsophisticated and slow. It will probably get better
as the collections of bugs we manage with it grow in size.

It's probably suitable for projects with at most hundreds of bugs.

It is not difficult to modify it to support more bugs.

Bugs.txt assumes you're using [git](http://git-scm.com/) - but only a
few lines need to be changed to accomodate another DVCS (or VCS, for
that matter, but that would be rather pointless).

## Install and System Requirements

You need a working [Python](http://python.org) (2.6+) install with
[web.py](http://webpy.org).

Export the bugs.txt repository into your sources (or clone it and
delete the `.git` directory).

You need a valid email configured in your git configuration (i.e. you
have run something like `git config --global user.email
"your_email@example.com"`). 

## Configuration

There is a `config.json` file that you can use to customize bugs.txt.

It has the following sections:

 * `users` - the list of users to be listed as possible assignees for
   bugs; it's not mandatory to fill in this list, but it may help with
   versioning conflicts;
 * `statuses` - the list of statuses for your bugs;
 * `closedStatus` - bugs having this status are considered closed;
 * `newStatus` - the status assigned to new bugs.

## Workflow

Whenever you need to edit bugs, launch the `bugstxt.py` file. It will
start a local web server and point the browser to the relevant page.

When you're done, close `bugstxt.py` (ctrl-C). Commit/push your
changes to make them available to others.

If there is a versioning conflict, use your merge tools to solve the
conflicts. This should be relatively easy, as the bugs are stored in
text files separated by section headers.


