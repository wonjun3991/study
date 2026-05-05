#!/bin/bash
# Post-edit hook: compile check for Java files
# Catches compilation errors early after Edit/Write operations

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only process Java files in src/main or src/test
if [[ "$FILE_PATH" != *.java ]]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR" || exit 0

# Determine which compile task to run based on file location
if [[ "$FILE_PATH" == */src/test/* ]]; then
  RESULT=$(./gradlew compileTestJava 2>&1)
else
  RESULT=$(./gradlew compileJava 2>&1)
fi

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  # Extract only the error lines (not the full Gradle output)
  ERRORS=$(echo "$RESULT" | grep -A 2 "error:" | head -20)
  echo "Compilation failed after editing $FILE_PATH"
  echo ""
  echo "$ERRORS"
  exit 1
fi

exit 0
