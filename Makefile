MESOS_SRC_DIR = mesos/src
MESOS_INCLUDE_DIRS = -I$(MESOS_SRC_DIR)
MESOS_INCLUDE_DIRS += -Imesos/include
PROTOS_DIR= $(MESOS_SRC_DIR)/messages/
OUTPUT_DIR=.

messages_pb2: $(wildcard $(PROTOS_DIR)*.proto)
	protoc $(MESOS_INCLUDE_DIRS) --python_out=$(OUTPUT_DIR) $(wildcard $(PROTOS_DIR)*.proto)

clean:
	rm -r $(OUTPUT_DIR)/messages
