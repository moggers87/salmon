#/bin/sh

# start logging server
mkdir logs run
./bin/salmon log -pid "./log.pid" -port 8899

# run tests
python setup.py test
return_code=$?

# stop logging server
./bin/salmon stop -pid "./log.pid"
rm -r logs run

exit $return_code
