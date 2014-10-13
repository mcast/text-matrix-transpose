#! /usr/bin/env python3

import sys

def main():
    args = sys.argv[1:]

    transposed = args[0] == '-T'
    if transposed:
        args.pop(0)

    # original problem size
    width = range(0, 4778)
    height = range(0, 1055133)

    edgeX = []
    edgeY = []


    for y in height:
        for x in width:
            

if __name__ == '__main__':

    # from https://docs.python.org/3/library/profile.html#profile.Profile
#    import cProfile, pstats, io
#    pr = cProfile.Profile()
#    pr.enable()

    main()
