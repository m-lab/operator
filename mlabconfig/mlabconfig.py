#!/usr/bin/python

import os
import sys
import yaml


def main():
    print sys.argv
    with open('config.yaml', 'r') as config:
        d = yaml.load_all(config)
        print 'obj', d
        for i in d:
            print 'i', i

        #print type(i), i
        yaml.dump(i, stream=sys.stdout, default_flow_style=False)
        #sys.stdout.flush()
        foo = {
            'name': 'foo',
            'my_list': [{'foo': 'test', 'bar': 'test2'}, {'foo': 'test3', 'bar': 'test4'}],
            'hello': 'world'
        }

        #print yaml.dump(foo, default_flow_style=False)


if __name__ == "__main__":
    main()
