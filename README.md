# text-matrix-transpose

Aims.

0. Do it in Python.
1. Transpose a matrix of space-separated cells (numbers, words, whatever)
   stored in a file.
2. Do not assume that even one row of this file will fit in memory.

Why?
* To [learn Python in the local user group](https://github.com/pynxton)
* Because an [interesting problem](http://codereview.stackexchange.com/questions/64370/transpose-a-large-matrix-in-python3) presented.
* [Extrinsic](https://en.wikipedia.org/wiki/Chocolate_brownie) [rewards](http://www.lego.com).  Thanks!

## Conventions

Suffix `U` means untransposed (original, input).  Suffix `T` means transposed (output).

## Algorithm outline
1. On every pass, stream one column`U` == row`T` to the output.
  * There is no need to buffer, just take the '''n'''th column and write it straight out.
  * Collect other cells in memory, to be written when the `rowT` is complete and the output file is ready for it.
  * Forget anything which isn't going to fit in the memory budget.
2. One the first pass,
  * discover the shape of the matrix
  * record `tell()` per row
  * do as much work as seems to be possible
3. On subsequent passes,
  * now you know how many columns`U` will fit in memory.  Don't read any more.
  * seek to the next cell for reading.  It's a separate pointer for each row.
  * read enough bytes to be sure you will have the number of cells you need, but no more.
  * write each completed row
4. Repeat until finished.

## Extensions
* Consider compressing (LZ4 or LZO?) the text, to trade CPU for extra memory budget.
* Using disk storage as intermediate solution for the column storage is another approach.

## Caveats

* It's not really my first Python program - I have poked Python code several times, just a little bit.
* It's also not mine, because it was Tommy's when I started.
* Testing has been ad-hoc, and is not automated.
* Performance measurements I made were mostly before/after some
  change, so are not absolute, objective or recorded anywhere.  The
  history is in the source.
