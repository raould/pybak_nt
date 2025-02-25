#!/usr/local/bin/perl -w

package anagram;

use wordHash;

sub getStats { return( wordHash::getStats() ); }

# when you are asked for the
# anangram of a word, see if there
# is already results for it and return
# those, otherwise generate.
# then start at the bottom...

sub anagram
{
    my( $word ) = shift;

    return( anagram_len( $word, length($word) ) );
}

sub anagram_len
{
    my( $word ) = shift;
    my( $len ) = shift;

    if( 1 == $len )
    {
	return
    }

    if( !defined($word) ) { print( "word?\n" ); exit(1); }
    $word = orderWord( $word );

    my( @rez ) = anagrams( $word );
    @rez = sort( @rez );

    return( @rez );
}

sub anagrams
{
    my( $word ) = shift;
    my( @grams );

    $word = orderWord( $word );
    #print( ">anagrams $word\n" );

    # get anagrams of all lesser words.
    # lesser word is current word with a letter removed.
    # then, insert the removed letter in all possible
    # places in lesser anagrams.

    if( length($word) <= 1 )
    {
	@grams = ( $word );
    }
    else
    {
	my( @check ) = lookup( $word );
	if( scalar(@check) > 0 )
	{
	    #print( "$word cached: [", join( ", ", @check ), "]\n" );
	    @grams = @check;
	}
	else
	{
	    # get all lesser words.
	    #print( "$word not cached, generating...\n" );

	    my( $index );
	    my( $letter );
	    my( $shorty );
	    my( @pairGrams );

	    for( $index = 0; $index < length($word); $index++ )
	    {
		$letter = substr( $word, $index, 1 );
		##print( "letter = $letter\n" );
		$shorty = removePos( $word, $index );
		##print( "shorty = $shorty\n" );

		@pairGrams = pairGrams( $shorty, $letter );
		##print( $shorty . "'s grams = ", join( ", ", @pairGrams ), "\n" );
		push( @grams, @pairGrams );
	    }

	    store( $word, @grams );
	    @grams = lookup( $word ); # uniq.
	    #print( "grams = ", join( ", ", @grams ), "\n" );
	}
    }

    #print( "<anagrams\n" );

    return( @grams );
}

sub pairGrams
{
    my( $short ) = shift;
    my( $letter ) = shift;
    my( @grams );

    #print( ">pairGrams $short $letter\n" );

    # get all shorter anagrams.

    my( @allSubGrams );
    my( @shortsGrams );
    @shortsGrams = anagrams( $short );
    ##print( $short . "'s grams = ", join( ", ", @shortsGrams ), "\n" );
    push( @allSubGrams, @shortsGrams );

    # now splice in the letter.

    my( @biggerShortsGrams );
    foreach $shorterGram ( @allSubGrams )
    {
	@biggerShortsGrams = allBigger( $shorterGram, $letter );
	##print( $shorterGram, "'s bigger grams = ", join( ", ", @biggerShortsGrams ), "\n" );
	push( @grams, @biggerShortsGrams );
    }

    #print( "<pairGrams\n" );

    return( @grams );
}

sub allBigger
{
    my( $word ) = shift;
    my( $letter ) = shift;
    my( @all );

    #print( ">allBigger\n" );

    my( $index );
    my( $new );
    for( $index = 0; $index <= length( $word ); $index++ )
    {
	$new = substr( $word, 0, $index );
	$new .= $letter;
	$new .= substr( $word, $index, length($word) );
	push( @all, $new );
    }

    #print( "<allBigger\n" );

    return( @all );
}

sub removePos
{
    my( $word ) = shift;
    my( $pos ) = shift;
    my( $shorty );

    if( $pos >= length($word) )
    {
	die( "removePos: pos beyond word length" );
    }

    $shorty = substr( $word, 0, $pos );
    $shorty .= substr( $word, $pos+1, length($word) );

    return( $shorty );
}

sub explode
{
    my( $word ) = shift;
    my( @letters ) = @_;

    my( $index );
    for( $index = 0; $index < length( $word ); $index++ )
    {
	push( @letters, substr( $word, $index, 1 ) );
    }

    return( @letters );
}


sub orderWord
{
    my( $word ) = shift;

    my( @letters ) = explode( $word );
    @letters = sort( @letters );
    $word = join( "", @letters );

    return( $word );
}

sub lookup
{
    my( $word ) = shift;
    my( @ray );

    #print( ">lookup $word\n" );

    @ray = wordHash::getList( $word );

    #print( "<lookup [", join( ", ", @ray ), "]\n" );

    return( @ray );
}

sub store
{
    my( $word ) = shift;
    my( @grams ) = @_;

    #print( ">store $word [@grams]\n" );

    wordHash::addList( $word, @grams );

    #print( "<store\n" );
}

sub countMaxGrams
{
    my( $word ) = shift;

    my( $count );
    $count = factorial( length($word) );

    return( $count );
}

sub countGrams
{
    my( $word ) = shift;
    
    my( $count );

    $count = countMaxGrams( $word );

    my( $sorted ) = orderWord( $word );
    my( @letters ) = explode( $sorted );
    my( @repeatCounts ) = countRepeats( @letters );

    my( $overCount ) = 1;
    my( $repeatCount );
    foreach $repeatCount ( @repeatCounts )
    {
	$overCount *= factorial( $repeatCount );
    }

    $count /= $overCount;

    return( $count );
}

sub countRepeats
{
    my( @list ) = @_;

    my( %hash );
    my( $index );
    for( $index = 0; $index < scalar(@list); $index++ )
    {
	if( !defined( $hash{ $list[$index] } ) )
	{
	    $hash{ $list[$index] } = 1;
	}
	else
	{
	    $hash{ $list[$index] }++;
	}
    }

    return( values( %hash ) );
}

sub factorial
{
    my( $val ) = shift;

    my( $fact ) = 1;

    while( $val > 0 )
    {
	$fact *= $val;
	$val--;
    }

    return( $fact );
}

1;
