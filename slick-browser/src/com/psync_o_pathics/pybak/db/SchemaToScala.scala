package com.psync_o_pathics.pybak.db
import scala.slick.model.codegen._

object SchemaToScala {
  def main( args:Array[String] ) {
    require(
      args.length == 5,
      "required arguments: slick-driver jdbc-driver jdbc-url dst-dir dst-package. got: '" + args.deep.mkString("', '") + "'"
    )
    val connectionSpec = args.slice( 0, 5 )
    SourceCodeGenerator.main( connectionSpec )
  }
}

