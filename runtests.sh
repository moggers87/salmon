#/bin/sh

# start logging server
mkdir logs run
./bin/salmon log -pid "./log.pid" -port 8899

# run tests
python setup.py nosetests
return_code=$?

# stop logging server
./bin/salmon stop -pid "./log.pid"
if [ $return_code == 0 ]; then
    rm -r logs run
fi

exit $return_code
