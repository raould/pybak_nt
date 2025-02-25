package wordHash;

use statHash;

sub getStats { return( statHash::getStats() ); }

my( %superHash );

sub getRefNonNull
{
    my( $key ) = shift;
    my( $hashRef ) = shift;

    my( $hRef );

    $hRef = $hashRef->{ $key };
    if( ! defined( $hRef ) )
    {
	$hRef = {};
	$hashRef->{ $key } = $hRef;
    }

    return( $hRef );
}

sub getList
{
    my( $key ) = shift;

    my( @list );
    my( $hRef );

    $hRef = getRefNonNull( $key, \%superHash );
    @list = keys( %{$hRef} );
    @list = sort( @list );

    if( scalar(@list) > 0 )
    {
      statHash::recordGotSomething();
    }
    else
    {
      statHash::recordGotBlank();
    }

    return( @list );
}

sub addList
{
    my( $key ) = shift;
    my( @list ) = @_;

    my( $hRef );

    $hRef = getRefNonNull( $key, \%superHash );

    foreach $elem ( @list )
    {
	$hRef->{ $elem } = 1;
    }

    statHash::recordStore();
}

1

