MESOS_SRC_DIR = mesos/src
MESOS_INCLUDE_DIR = mesos/include

MESOS_INCLUDE_DIRS += -I$(MESOS_SRC_DIR)
MESOS_INCLUDE_DIRS += -I$(MESOS_INCLUDE_DIR)

MESSAGES_SRC = $(MESOS_SRC_DIR)/messages
MESOS_SRC += $(MESOS_INCLUDE_DIR)/mesos
RESOURCE_SRC += $(MESOS_INCLUDE_DIR)/mesos/resource_provider

OUTPUT_DIR = protobufs

PROTO_SRC = $(addprefix messages/,$(notdir $(wildcard $(addsuffix /*.proto,$(MESSAGES_SRC)))))
PROTO_SRC += $(addprefix mesos/,$(notdir $(wildcard $(addsuffix /*.proto,$(MESOS_SRC)))))
PROTO_SRC += $(addprefix mesos/resource_provider/,$(notdir $(wildcard $(addsuffix /*.proto,$(RESOURCE_SRC)))))
PROTO_SRC_DIR = $(wildcard $(addsuffix /*.proto,$(PROTO_DIRS)))

all: protobuf

$(OUTPUT_DIR):
	mkdir -p $(OUTPUT_DIR)

protobuf: $(PROTO_SRC_DIR) $(OUTPUT_DIR)
	protoc $(MESOS_INCLUDE_DIRS) --python_out=$(OUTPUT_DIR) $(PROTO_SRC)

.PHONY: clean decode
clean:
	rm -rf $(OUTPUT_DIR)

.SILENT: decode
decode:
	echo "What is the message type?"; \
	read messageType;\
	echo "What is the message binary?"; \
	read binary; \
	echo "\n\n";\
	echo "$$binary" | xxd -r -p - | protoc $(MESOS_INCLUDE_DIRS) --decode=$$messageType $(PROTO_SRC)
