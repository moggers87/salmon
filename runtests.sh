#/bin/sh

# start logging server
mkdir logs run
python -c "from salmon import commands; commands.main()" log --pid "./log.pid" --port 8899

# run tests
python setup.py nosetests
return_code=$?

# stop logging server
python -c "from salmon import commands; commands.main()" stop --pid "./log.pid"
if [ $return_code == 0 ]; then
    rm -r logs run
fi

exit $return_code
