#! /usr/bin/env python3
import sys
import os

def main():
    path_in = sys.argv[-1]
    with open(path_in) as fd_in:
        while True:
            line = fd_in.readline()
            if line == '':
                break
            print("%d: %s" % (len(line)-1, line), end='')
    return


if __name__ == '__main__':
    main()
