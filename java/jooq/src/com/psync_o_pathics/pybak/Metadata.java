package com.psync_o_pathics.pybak;

import com.nebhale.jsonpath.*;
import com.psync_o_pathics.pybak.util.*;
import java.util.*;
import java.io.*;
import java.nio.file.*;
import java.nio.charset.*;
import org.json.simple.*;
import org.json.simple.parser.*;
import org.junit.*;
import org.junit.Test;
import static org.junit.Assert.*;
import org.apache.commons.lang3.*;
import static org.apache.commons.lang3.StringUtils.*;
import org.apache.commons.collections4.*;
import static org.apache.commons.collections4.CollectionUtils.*;

// (This is currently version 10 in the python code.)
// new metadata schema is a dict like this example:
//
// (note that strings in python are, i think, just
// a series of bytes which means they can represent
// things like ext{3,4} unix paths that are just bytes.
// so i am leaving them 'clear' in the python md, but
// am hexlifying for json.)
//
// { VERSION_KEY => int
//   HOSTS_KEY =>
//    { host =>
//       { PY_PLATFORM_SYSTEM_KEY => string
//         PY_PLATFORM_UNAME_KEY => string
//         PY_BYTEORDER_KEY => string
// - todo: should really make another version where
// - PATHS_KEY becomes HEXL_PATHS_KEY and
// - FILEPATH_PARTS_KEY becomes HEXL_FILEPATH_PARTS_KEY.
// - we don't know if our exported metadata did twice-hexl-ing.
//        PATHS_KEY =>
//              { clear-path in runtime metadata, hexl-path in mdj =>
//                 { LAST_UPDATE_SEC_KEY => seconds
//                  OLDEST_TIMESTAMP_KEY => seconds
//                  EXE_KEY => is_executable
//                   FILEPATH_PARTS_KEY => (clear/hexl)[path,to,file] (unfortunately, historically, optional.)
//                   PY_FILEPATH_ENCODING_KEY => 'utf-8'
//                   PY_PATH_SEP_KEY => string # clear-text. (unfortunately?!)
// } } } }

public class Metadata {

  private static final String UNKNOWN_VALUE="unknown_value"; // hopefully no e.g. hosts we crawl are called that.
  private static final String RAW_BYTES_ENCODING="RAW_BYTES"; // see CustomEncodings.java
  private static final String DEFAULT_ENCODING=RAW_BYTES_ENCODING;
  private static final String RUNTIME_MIGRATED_KEY="runtime_migrated"; // do not include in de/seriailzation.
  private static final int CURRENT_VERSION=10;
  private static final String STASHED_KEY="stashed";
  private static final String VERSION_KEY="version";
  private static final String HOSTS_KEY="hosts";
  private static final String PATHS_KEY="paths";
  private static final String LAST_UPDATE_SEC_KEY="last-update-sec";
  private static final String OLDEST_TIMESTAMP_KEY="oldest-timestamp";
  private static final String EXE_KEY="exe";
  private static final String FILEPATH_PARTS_KEY="filepath_parts";
  private static final String DEPRECATED_FILEPATH_ENCODING_KEY="filepath_encoding";
  private static final String PY_FILEPATH_ENCODING_KEY="py_filepath_encoding";
  private static final String PY_PLATFORM_SYSTEM_KEY="py_platform_system";
  private static final String PY_PLATFORM_UNAME_KEY="py_platform_uname";
  private static final String PY_BYTEORDER_KEY="py_byteorder";
  private static final String PY_PATH_SEP_KEY="py_path_sep";
  public static final String PICKLE_DOTEXT=".metadata";
  public static final String JSON_DOTEXT=".mdj";
  private static final String DEFAULT_PATH_SEP="/";

  // ----------------------------------------

  public static final Metadata fromJsonString( String json ) {
	JSONParser parser = new JSONParser();
	try {
	  Object obj = parser.parse(json);
	  JSONObject jsonObject = (JSONObject) obj;
	  return new Metadata( jsonObject );
	} catch (ParseException e) {
	  e.printStackTrace();
	}
	System.exit(0);
	return null;
  }

    public static final Metadata fromPath( Path path ) {
	JSONParser parser = new JSONParser();
	try {
	    Object obj = parser.parse(new FileReader(path.toFile()));
	    JSONObject jsonObject = (JSONObject) obj;
	    return new Metadata( jsonObject );
	} catch (FileNotFoundException e) {
	    e.printStackTrace();
	} catch (IOException e) {
	    e.printStackTrace();
	} catch (ParseException e) {
	    e.printStackTrace();
	}
	System.exit(0);
	return null;
    }

  private final JSONObject jsonObject;

  private Metadata( JSONObject jsonObject ) {
	this.jsonObject = jsonObject;
  }

  public int getVersion() {
	return JsonPath.read(JsonPathUtil.buildPath(VERSION_KEY),
						 jsonObject.toString(),
						 Integer.class);
  }

  public Set<String> getHostNames() {
	return JsonPath.read(JsonPathUtil.buildPath(HOSTS_KEY),
						 jsonObject.toString(),
						 SortedMap.class).keySet();
  }

  public String getPyPlatformSystemKey( String hostName ) {
	return JsonPath.read(JsonPathUtil.buildPath(HOSTS_KEY, hostName, PY_PLATFORM_SYSTEM_KEY),
						 jsonObject.toString(),
						 String.class);
  }

  public String getPyPlatformUnameKey( String hostName ) {
	return JsonPath.read(JsonPathUtil.buildPath(HOSTS_KEY, hostName, PY_PLATFORM_UNAME_KEY),
						 jsonObject.toString(),
						 String.class);
  }

  public String getPyByteorderKey( String hostName ) {
	return JsonPath.read(JsonPathUtil.buildPath(HOSTS_KEY, hostName, PY_BYTEORDER_KEY),
						 jsonObject.toString(),
						 String.class);
  }

  public Set<String> getPaths( String hostName ) {
	  return JsonPath.read(JsonPathUtil.buildPath(HOSTS_KEY, hostName, PATHS_KEY),
						 jsonObject.toString(),
						 SortedMap.class).keySet();
  }

  public Long getLastUpdateSec( String hostName, String path ) {
	return JsonPath.read(JsonPathUtil.buildPath(HOSTS_KEY, hostName, PATHS_KEY, path, LAST_UPDATE_SEC_KEY),
						 jsonObject.toString(),
						 Long.class);
  }

  public Long getOldestTimestampSec( String hostName, String path ) {
	return JsonPath.read(JsonPathUtil.buildPath(HOSTS_KEY, hostName, PATHS_KEY, path, OLDEST_TIMESTAMP_KEY),
						 jsonObject.toString(),
						 Long.class);
  }

  public Boolean getIsExe( String hostName, String path ) {
	final Object b = JsonPath.read(JsonPathUtil.buildPath(HOSTS_KEY, hostName, PATHS_KEY, path, EXE_KEY),
								   jsonObject.toString(),
								   Object.class);
	final String bs = String.valueOf(b).toLowerCase().trim();
	return "true".equals(bs);
  }

  public List<String> getFilepathParts( String hostName, String path ) {
	return JsonPath.read(JsonPathUtil.buildPath(HOSTS_KEY, hostName, PATHS_KEY, path, FILEPATH_PARTS_KEY),
						 jsonObject.toString(),
						 List.class);
  }

  public String getFilepathEncoding( String hostName, String path ) {
	return JsonPath.read(JsonPathUtil.buildPath(HOSTS_KEY, hostName, PATHS_KEY, path, PY_FILEPATH_ENCODING_KEY),
						 jsonObject.toString(),
						 String.class);
  }

  public String getPathSep( String hostName, String path ) {
	return JsonPath.read(JsonPathUtil.buildPath(HOSTS_KEY, hostName, PATHS_KEY, path, PY_PATH_SEP_KEY),
						 jsonObject.toString(),
						 String.class);
  }

  public String toString() {
	return jsonObject.toJSONString();
  }

  //----------------------------------------

  public static final class Tester {
	@Test
	public void test_getVersion() {
	  final Metadata m = Metadata.fromJsonString( getJson() );
	  assertEquals( -1, m.getVersion() );
	}
	@Test
	public void test_getHostNames() {
	  final Metadata m = Metadata.fromJsonString( getJson() );
	  assertEquals( 2, m.getHostNames().size() );
	  assertEquals( "h1", m.getHostNames().toArray()[0] );
	  assertEquals( "h2", m.getHostNames().toArray()[1] );
	}
	@Test
	public void test_getPyPlatformSystemKey() {
	  final Metadata m = Metadata.fromJsonString( getJson() );
	  assertEquals( "ppsk1", m.getPyPlatformSystemKey("h1") );
	}
	@Test
	public void test_getPaths() {
	  final Metadata m = Metadata.fromJsonString( getJson() );
	  assertEquals( 1, m.getPaths("h1").size() );
	  assertEquals( "p1", m.getPaths("h1").toArray()[0] );
	}
	@Test
	public void test_getLastUpdateSec() {
	  final Metadata m = Metadata.fromJsonString( getJson() );
	  assertEquals( (Long)42l, m.getLastUpdateSec("h1","p1") );
	}
	@Test
	public void test_getIsExe() {
	  final Metadata m = Metadata.fromJsonString( getJson() );
	  assertEquals( Boolean.TRUE, m.getIsExe("h1","p1") );
	}
	@Test
	public void test_getFilepathParts() {
	  final Metadata m = Metadata.fromJsonString( getJson() );
	  assertEquals( 1, m.getFilepathParts("h1","p1").size() );
	  assertEquals( "p1", m.getFilepathParts("h1","p1").get(0) );
	}
	@Test
	public void test_getFilepathEncoding() {
	  final Metadata m = Metadata.fromJsonString( getJson() );
	  assertEquals( "RAW_BYTES", m.getFilepathEncoding("h1","p1") );
	}
	@Test
	public void test_getPathSep() {
	  final Metadata m = Metadata.fromJsonString( getJson() );
	  assertEquals( "/", m.getPathSep("h1","p1") );
	}
	private static final String getJson() {
	  final Object o = JSONValue.parse
		(
		 "{\"version\":-1,\"hosts\":{\"h2\":{},\"h1\":{\"py_platform_system\":\"ppsk1\",\"py_platform_uname\":\"unknown_value\",\"py_byteorder\":\"unknown_value\",\"paths\":{\"p1\":{\"filepath_parts\":[\"p1\"],\"exe\":\"True\",\"last-update-sec\":42,\"oldest-timestamp\":1423579774,\"py_path_sep\":\"/\",\"py_filepath_encoding\":\"RAW_BYTES\"}}}}}"
		 );
	  return o.toString();
	}
  }
}
