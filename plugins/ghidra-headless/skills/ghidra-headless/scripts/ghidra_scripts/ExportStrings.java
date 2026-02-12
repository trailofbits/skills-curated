/* ###
 * Export all strings found in the binary
 * @category Export
 */

import ghidra.app.script.GhidraScript;
import ghidra.program.model.data.DataType;
import ghidra.program.model.data.StringDataType;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.util.DefinedDataIterator;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;

public class ExportStrings extends GhidraScript {

    @Override
    public void run() throws Exception {
        String outputDir = System.getenv("GHIDRA_OUTPUT_DIR");
        if (outputDir == null || outputDir.isEmpty()) {
            outputDir = ".";
        }

        String programName = currentProgram.getName().replaceAll("[^a-zA-Z0-9._-]", "_");
        File outputFile = new File(outputDir, programName + "_strings.json");

        println("Exporting strings to: " + outputFile.getAbsolutePath());

        try (PrintWriter writer = new PrintWriter(new FileWriter(outputFile))) {
            writer.println("{");
            writer.println("  \"program\": \"" + escapeJson(currentProgram.getName()) + "\",");
            writer.println("  \"strings\": [");

            int count = 0;
            boolean first = true;

            // Iterate through all defined data looking for strings
            DataIterator dataIterator = currentProgram.getListing().getDefinedData(true);

            while (dataIterator.hasNext() && !monitor.isCancelled()) {
                Data data = dataIterator.next();

                if (isStringData(data)) {
                    String value = getStringValue(data);
                    if (value != null && !value.isEmpty() && value.length() >= 4) {  // Skip very short strings
                        if (!first) {
                            writer.println(",");
                        }
                        first = false;

                        writer.println("    {");
                        writer.println("      \"address\": \"" + data.getAddress() + "\",");
                        writer.println("      \"type\": \"" + data.getDataType().getName() + "\",");
                        writer.println("      \"length\": " + value.length() + ",");
                        writer.println("      \"value\": \"" + escapeJson(truncate(value, 1000)) + "\"");
                        writer.print("    }");
                        count++;
                    }
                }
            }

            writer.println();
            writer.println("  ]");
            writer.println("}");

            println("Exported " + count + " strings");
        }
    }

    private boolean isStringData(Data data) {
        DataType dt = data.getBaseDataType();
        String typeName = dt.getName().toLowerCase();
        return typeName.contains("string") || 
               typeName.equals("char") ||
               typeName.contains("unicode");
    }

    private String getStringValue(Data data) {
        Object value = data.getValue();
        if (value instanceof String) {
            return (String) value;
        }
        // Try to get the string representation
        String repr = data.getDefaultValueRepresentation();
        if (repr != null && repr.startsWith("\"") && repr.endsWith("\"")) {
            return repr.substring(1, repr.length() - 1);
        }
        return repr;
    }

    private String truncate(String s, int maxLen) {
        if (s == null) return "";
        if (s.length() <= maxLen) return s;
        return s.substring(0, maxLen) + "...";
    }

    private String escapeJson(String s) {
        if (s == null) return "";
        StringBuilder sb = new StringBuilder();
        for (char c : s.toCharArray()) {
            switch (c) {
                case '\\': sb.append("\\\\"); break;
                case '"': sb.append("\\\""); break;
                case '\n': sb.append("\\n"); break;
                case '\r': sb.append("\\r"); break;
                case '\t': sb.append("\\t"); break;
                case '\b': sb.append("\\b"); break;
                case '\f': sb.append("\\f"); break;
                default:
                    if (c < 32 || c > 126) {
                        sb.append(String.format("\\u%04x", (int) c));
                    } else {
                        sb.append(c);
                    }
            }
        }
        return sb.toString();
    }
}
