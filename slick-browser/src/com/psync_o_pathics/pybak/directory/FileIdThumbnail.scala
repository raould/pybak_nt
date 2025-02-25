package com.psync_o_pathics.pybak.directory

import scala.collection.mutable._
import com.psync_o_pathics.pybak._
import com.psync_o_pathics.pybak.util._

class FileIdThumbnail( val name:String, val canonicalId:Int, val thumbnail:Option[JpegType.Jpeg] ) {}
