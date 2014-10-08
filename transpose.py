#! /usr/bin/env python3
import sys
import os


def main():

    path_in = sys.argv[-1]
    path_out = os.path.basename(path_in)+'.transposed'
    separator = ' '

    with open(path_in) as fd_in:
        line = fd_in.readline()
    rows2 = cols1 = len(line.split(separator))
    del line

    in_seek = {}
    out_len = {}
    longval = 0                 # including a separator
    for x in range(cols1):
        out_len[x] = 0

    with open(path_in) as fd_in:
        i = 0
        print('indexing')
        while True:
            tell = fd_in.tell()
            line = fd_in.readline()
            in_seek[i] = tell
            if line == '':
                break
            row = line.split(separator)
            if len(row) != cols1:
                raise Exception("%d: column count mismatch (got %d, expect %d)" %
                                (i+1, len(row), cols1))
            for x in range(cols1):
                lenval = (len(row[x])
                          + (1,0)[x == cols1-1]) # for the separator
                out_len[x] += lenval
                if lenval > longval:
                    longval = lenval
            i += 1
        print('indexed')
    cols2 = rows1 = i
    longrow = max(out_len.values())

    print('in_seek = ' + repr(in_seek.values()))
    print('out_len = ' + repr(out_len.values()), ", longest = ", longrow)

    # in-place would save space; rename?
    out_pos = { 0: 0}
    for x in range(cols1):
        out_pos[x+1] = out_pos[x] + out_len[x]

    print('out_pos = ' + repr(out_pos.values()))

    with open(path_in) as fd_in, open(path_out, 'w') as fd_out:
        print('transposing')
        for row2 in range(rows2):
            print('row', row2)
            for row1 in range(rows1):
                fd_in.seek(in_seek[row1])
                s = ''
                chars = fd_in.read(longval)
                while True:
                    char = chars[0]
                    chars = chars[1:]
                    if char == separator or char == '\n':
                        break
                    s += char
                in_seek[row1] += len(s)+1
                if row1+1 < rows1:
                    fd_out.write('{} '.format(s))
                else:
                    fd_out.write('{}\n'.format(s))

    return


if __name__ == '__main__':
    main()
