#!/usr/local/bin/perl5 -w

# find variables in given file.
# get variables & values from given hash.
# replace variables with values.

package template;

my( $varDelim ) = "\\\{";
my( $colDelim ) = "\\\[";
my( $optDelim ) = "\\\}";

sub singlesSub
{
    my( $strRef ) = shift;
    my( $vdRef ) = shift;

    $strRef = lineSub( $strRef, $vdRef );

    return( $strRef );
}

sub tableSub
{
    my( $strRef ) = shift;
    my( $rowsRef ) = shift;

    my( %uberHash );
    my( $rvals );
    my( @rows ) = @{$rowsRef};
    foreach $rvals( @rows )
    {
	my( $key, $value );

	foreach $key ( keys(%{$rvals}) )
	{
	    $value = $rvals->{ $key };
	    $uberHash{ $key } = $value;
	}
    }

    $strRef = expandTableDefs( $strRef, $rowsRef, \%uberHash );

    return( $strRef );
}

####################

sub expandTableDefs
{
    my( $strRef ) = shift;
    my( $rowsRef ) = shift;
    my( $valsRef ) = shift;

    # assumes the table defs are each on their own line.
    my( @lines ) = split( /\n/, $$strRef );
    my( @rows ) = @{$rowsRef};

    foreach ( @lines )
    {
	chomp;

	if( $_ =~ m/tableDef/ )
	{
	    # expecting "tableDef:C1:C2:C3"
	    # inside each C there can be
	    # variables which are delimited
	    # by $varDelim, and which need to have
	    # their row number added to 'em.

	    # break up the table def on the col boundaries.
	    my( @parts ) = split( /$colDelim/, $_ );

            # ditch "tableDef";
	    shift( @parts );

	    my( $rc );
	    for $rc ( 0 .. $#rows )
	    {
		my( $row );
		my( $colStr );
		my( $options );

		$row = "<tr>";
		foreach $colStr ( @parts )
		{
		    #print( "<!-- colStr=$colStr -->\n" );
		    $options = getOptions( $colStr );
		    $row .= "<td $options>" . processCol( $colStr, $rc, $valsRef ) . "</td>";
		}
		$row .= "</tr>\n";

		push( @newLines, $row );
	    }
	}
	else
	{
	    push( @newLines, "$_\n" );
	}
    }

    my( $str ) = join( "", @newLines );

    return( \$str );
}

sub getOptions
{
    my( $str ) = shift;

    my( $opt ) = "";
    if( $str =~ m/$optDelim([^$optDelim]*?)$optDelim/ )
    {
	$opt = $1;
    }

    return( $opt );
}

sub processCol
{
    my( $rowStr ) = shift;
    my( $rc ) = shift;
    my( $valsRef ) = shift;

    # assume that options have already
    # been sucked out, so we can now delete them.
    $rowStr =~ s/$optDelim[^$optDelim]*?$optDelim//g;

    #$rowStr =~ s/$varDelim([^$varDelim]*?)$varDelim/$varDelim$1\_$rc$varDelim/g;    

    while( $rowStr =~ m/$varDelim([^$varDelim]*?)$varDelim/ )
    {
	my( $var ) = $1;
	my( $key ) = $var . '_' . $rc;
	my( $val ) = $valsRef->{ $key };
	if( !defined( $val ) ) { $val = ""; }
	#print( "<!-- key=$key val=$val -->\n" );
	$rowStr =~ s/$varDelim$var$varDelim/$val/g;
    }

    return( $rowStr );
}

####################

sub lineSub
{
    my( $strRef ) = shift;
    my( $vdRef ) = shift;
    
    my( @keys ) = keys( %{$vdRef} );
    my( $key, $val );
    foreach $key ( @keys )
    {
	$val = $vdRef->{ $key };
	#print( "<!-- key=$key val=$val -->\n" );

	if( !defined( $val ) ) { $val = ""; }
	$key = "$varDelim$key$varDelim";
	$$strRef =~ s/$key/$val/ig;
    }

    return( $strRef );
}
    
##

# ref to @rows of hashtable refs -> change the key in each to _$rowNum
sub appendRowIDs
{
    my( $rowsRef ) = shift;

    my( $rc ) = 0;

    my( @newRows );

    my( $hashRef );
    foreach $hashRef ( @{$rowsRef} )
    {
	my( %newHash );
	my( $key, $value );

	foreach $key ( keys(%{$hashRef}) )
	{
	    $value = $hashRef->{$key};
	    $newHash{ "$key" . '_' . "$rc" } = $value;
	}

	push( @newRows, \%newHash );
	$rc++;
    }

    return( \@newRows );
}

1;
