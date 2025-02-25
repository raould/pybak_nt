package bitgram;

sub anagram
{
    my($word) = shift;

    # figure out what the numerical
    # value of a bit vector of length($word)
    # of all ones would be.
    # length = 1...n
    # (2^n)-1
    # xx | n=2 | 2^2 = 4-1 = 3
    my($max) = (2 ** length($word))-1;

    my($index);
    my(@pos);
    my(@letters);
    my(@grams);

    for( $index = 1; $index <= $max; $index++ )
    {
	@pos = generatePositions( $index );
	@letters = getLetters( $word, @pos );
	push( @grams, join( "", @letters ) )
    }

    return( @grams );
}

sub getLetters
{
    my($word) = shift;
    my(@positions) = @_;

    my(@letters);

    foreach $pos ( @positions )
    {
	push( @letters, substr( $word, $pos, 1 ) );
    }

    return(@letters);
}

sub generatePositions
{
    my($num) = shift;
    my(@positions);

    my($pos) = 0;
    while( $num > 0 )
    {
	$low = ($num & 0x01);
	if( $low == 1 )
	{
	    push( @positions, $pos );
	}

	$num = $num >> 1;
	$pos++;
    }

    return(@positions);
}

1;
