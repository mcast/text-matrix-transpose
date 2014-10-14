#! /usr/bin/perl

package Transposer;

use strict;
use warnings;

use IO::Handle;
use List::Util qw( min );


=head1 NAME

Transposer - matrix transpose for large non-sparse textual-cell file

=head1 CONVENTIONS

Suffix conventions: U implies input (untransposed), T implies
output (transposed).  Hence rowsU == colsT and colsU == rowsT.

=cut

sub main {
  my ($pkg, $in) = @_;
  my ($out) = $in =~ m{(?:^|/)([^/]+)$} # unix-centric
    or die "can't get leaf of $in";
  $out .= '.transposed';

  open my $fh_in, '<', $in or die "Read $in: $!";
  open my $fh_out, '>', $out or die "Write $out: $!";

  my $transposer = $pkg->new($fh_in, $fh_out);
  $transposer->loop_until_done();
  return;
}

sub new {
  my ($pkg, $fh_in, $fh_out) = @_;

  my $self =
    { fd_in => $fd_in,
      fd_out => $fd_out,
      rowU_tell => [], # seek here to get next value from within the row
      rowT => {},      # collect output
      mem_budget => 100 * 1024 * 1024, # in bytes, ignoring overhead & rowU_tell
      separator => ' ',

      # no data yet
      colsU => -1,
      rowsU => -1,
      longcell => 0,		# without separator
      longrowU => 0,		# with \n
      shortrowU => -1,		# with \n
      colU_keepn => -1,
    };
  bless $self, $pkg;
  return $self;
}

sub rowsT { $_->[0]->{colsU} }
sub colsT { $_->[0]->{rowsU} }

sub colsU { $_->[0]->{colsU} }
sub rowsU { $_->[0]->{rowsU} }

sub colU_keepn { $_->[0]->{colU_keepn} }

sub fd_in { $_->[0]->{fd_in} }
sub fd_out { $_->[0]->{fd_out} }

sub loop_until_done {
  my ($self) = @_;
  my $passnum = 0;
  my $nextcolU = 0;
  while (1) {
    $nextcolU = $self->loop($passnum, $nextcolU);
    printf "  next loop = %s\n", nextcolU;
    last unless defined $nextcolU;
    $passnum ++;
  }
  return;
}

sub loop {
  my ($self, $passnum, $colU_start) = @_;
  my $rowU = 0;
  my $keep_colU; # init on first row, or subsequent pass
  if ($passnum == 0) {
    $self->{rowU_tell}[$rowU] = $self->fd_in->tell();
    $self->{fd_in_size} = -s $self->fd_in;
  } else {
    $self->fd_in->seek( $self->{rowU_tell}[0] )
___ or die ?;

    $keep_colU = Range->new($colU_start, min($self->colsU, $colU_start + $self->colU_keepn));

  }

  
}

__PACKAGE__->main(@ARGV) if caller();

1;



package Range;
sub new {
  my ($pkg, $start, $stop) = @_;
  return bless [ $start, $stop ], $pkg;
}
sub start { $_->[0][0] }
sub stop  { $_->[0][1] }

1;
