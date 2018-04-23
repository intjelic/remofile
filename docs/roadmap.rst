Roadmap
=======

While Remofile already features the most useful features, it still has a
list of features that could greatly enhances the software without
deviate from its simple concept philosophy.


file commands comes with -p to creates subdirectories andd -u command
also update the file timestamp


- compression level

-z, --compress              compress file data during the transfer

--compress-level=NUM    explicitly set compression level


Upcoming improvements.

- use a more efficient socket pattern; so far REQ-REP for simplicity but when it comes to transfering large files, fine-tuning of the underlying trasnfering mechanism could be done (UDP, chunk size); I'm not an expert.
- improve authentication mechanism to disable /warn when trying to access the served directory concurrently.
- Depythonization of the protocol; make it available to C level.

Investigate the following options. ::

    --max-delete=NUM        don't delete more than NUM files


    -z, --compress              compress file data during the transfer

    --compress-level=NUM    explicitly set compression level

    --progress              show progress during transfer


