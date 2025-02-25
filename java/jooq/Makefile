EMPTY :=
SPACE := $(EMPTY) $(EMPTY)

SRC_DIR=src
LIB_DIR=lib
BIN_DIR=bin
GEN_DIR=gen

JARS=$(shell find $(LIB_DIR) -name \*.jar)
CP = .:$(subst $(SPACE),:,$(JARS))

SRC=$(shell find $(SRC_DIR) -name \*.java)

DRIVER=org.postgresql.Driver
URL=jdbc:postgresql://192.168.123.65/pybakdb
USER=postgres
PASSWORD=postgres
CLOJURE_JAR=/home/superman/Bin/clojure/clojure-1.6.0/clojure-1.6.0.jar
SCALA=scala

build:
	mkdir -p $(BIN_DIR)
	javac -d $(BIN_DIR) -cp $(CP):gen $(SRC)

test: build
	java -cp $(CP):$(GEN_DIR):$(BIN_DIR) com.psync_o_pathics.pybak.test.RunAllTests

run: build
	java -cp $(CP):$(GEN_DIR):$(BIN_DIR) com.psync_o_pathics.pybak.DbUpsertMain /tmp/tmp/canonical $(USER) $(PASSWORD) $(URL) $(DRIVER)

scala-repl: build
	$(SCALA) -cp $(CP):$(GEN_DIR):$(BIN_DIR)
clj-repl: build
	java -cp $(CP):$(GEN_DIR):$(BIN_DIR):$(CLOJURE_JAR) clojure.main

clean:
	rm -rf $(BIN_DIR)
	mkdir -p $(BIN_DIR)
	find $(SRC_DIR) -name \*.class -delete

generate:
	rm -rf $(GEN_DIR)
	java -cp $(CP) org.jooq.util.GenerationTool generation.xml

