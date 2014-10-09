#! /usr/bin/env python3
import sys
import os


class TextTransposer:
    """Suffix conventions: U implies input (untransposed), T implies
    output (transposed).  Hence rowsU == colsT and colsU == rowsT.
    """

    separator = b' '

    def __init__(self, fd_in, fd_out):
        self.fd_in = fd_in
        self.fd_out = fd_out
        self.rowU_tell = {} # seek here to get next value from within the row
        self.pass1 = False  # have not yet seen the entire file
        self.rowT = {}      # collect output
        self.collected_size = 0 # in bytes, ignoring python overhead
        self.colsU = -1         # no data yet
        self.rowsU = -1         # no data yet

    def rowsT(self):
        return self.colsU
    def colsT(self):
        return self.rowsU

    def loop_until_done(self):
        passnum = 0
        nextcolU = 0
        while True:
            nextcolU = self.loop(passnum, nextcolU)
            if nextcolU == None:
                break

    def loop(self, passnum, colU_start):
        rowU = 0
        if passnum == 0:
            keep_colU = None    # init on first row
        else:
            keep_colU = range(colU_start, self.colsU)

        while True:
            line = self.fd_in.readline()
            if line == b'':
                break           # eof
            print("  got line='%s', sep='%s'\n" % (repr(line), self.separator))
            colsU = line.split(sep=self.separator)
            colsU[-1] = colsU[-1].rstrip(b'\n')
            print("  colsU=(%s)\n" % repr(colsU))
            if passnum == 0:
                if self.colsU < 0:
                    self.colsU = len(colsU)
                    keep_colU = range(colU_start, self.colsU)
                elif len(colsU) != self.colsU:
                    raise Exception("%d: column count mismatch (got %d, expect %d)" %
                                    (rowU+1, len(colsU), self.colsU))
                rowU += 1
                self.rowU_tell[rowU] = self.fd_in.tell()
            else:
                rowU += 1

            if rowU == 1:
                for x in keep_colU:
                    self.rowT[x]  = colsU[x] + (b' ',b'')[x == self.colsU]
            else:
                for x in keep_colU:
                    self.rowT[x] += colsU[x] + (b' ',b'')[x == self.colsU]

        for y in keep_colU:
            self.fd_out.write( self.rowT[y] + b'\n' )
        self.rowT = {}
        print("  done loop %d, next is col %d\n" % (passnum, keep_colU.stop))
        return keep_colU.stop


#    rows2 = cols1 = len()
#    del line
#
#    in_seek = {}
#    out_len = {}
#    longval = 0                 # including a separator
#    for x in range(cols1):
#        out_len[x] = 0
#
#    with open(path_in) as fd_in:
#        i = 0
#        print('indexing')
#        while True:
#            tell = fd_in.tell()
#            line = fd_in.readline()
#            in_seek[i] = tell
#            if line == '':
#                break
#            row = line.split(separator)
#
#            for x in range(cols1):
#                lenval = (len(row[x])
#                          + (1,0)[x == cols1-1]) # for the separator
#                out_len[x] += lenval
#                if lenval > longval:
#                    longval = lenval
#            i += 1
#        print('indexed')
#    cols2 = rows1 = i
#    longrow = max(out_len.values())
#
#    print('in_seek = ' + repr(in_seek.values()))
#    print('out_len = ' + repr(out_len.values()), ", longest = ", longrow)
#
#    # in-place would save space; rename?
#    out_pos = { 0: 0}
#    for x in range(cols1):
#        out_pos[x+1] = out_pos[x] + out_len[x]
#
#    print('out_pos = ' + repr(out_pos.values()))
#
#    with open(path_in,'b') as fd_in, open(path_out, 'wb') as fd_out:
#        print('transposing')
#        for row2 in range(rows2):
#            print('row', row2)
#            for row1 in range(rows1):
#                fd_in.seek(in_seek[row1])
#                s = ''
#                chars = fd_in.read(longval)
#                while True:
#                    char = chars[0]
#                    chars = chars[1:]
#                    if char == separator or char == '\n':
#                        break
#                    s += char
#                in_seek[row1] += len(s)+1
#                if row1+1 < rows1:
#                    fd_out.write('{} '.format(s))
#                else:
#                    fd_out.write('{}\n'.format(s))



def main():

    path_in = sys.argv[-1]
    path_out = os.path.basename(path_in)+'.transposed'
 
    with open(path_in,'rb') as fd_in, open(path_out, 'wb') as fd_out:
        transposer = TextTransposer(fd_in, fd_out)
        transposer.loop_until_done()

    return


if __name__ == '__main__':
    main()
