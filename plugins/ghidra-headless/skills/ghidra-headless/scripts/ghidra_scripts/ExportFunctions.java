/* ###
 * Export function list with addresses, signatures, and metadata as JSON
 * @category Export
 */

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Parameter;
import ghidra.program.model.symbol.SourceType;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;

public class ExportFunctions extends GhidraScript {

    @Override
    public void run() throws Exception {
        String outputDir = System.getenv("GHIDRA_OUTPUT_DIR");
        if (outputDir == null || outputDir.isEmpty()) {
            outputDir = ".";
        }

        String programName = currentProgram.getName().replaceAll("[^a-zA-Z0-9._-]", "_");
        File outputFile = new File(outputDir, programName + "_functions.json");

        println("Exporting functions to: " + outputFile.getAbsolutePath());

        try (PrintWriter writer = new PrintWriter(new FileWriter(outputFile))) {
            writer.println("{");
            writer.println("  \"program\": \"" + escapeJson(currentProgram.getName()) + "\",");
            writer.println("  \"architecture\": \"" + currentProgram.getLanguage().getProcessor() + "\",");
            writer.println("  \"functions\": [");

            FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
            boolean first = true;
            int count = 0;

            while (functions.hasNext() && !monitor.isCancelled()) {
                Function func = functions.next();

                if (!first) {
                    writer.println(",");
                }
                first = false;

                writer.println("    {");
                writer.println("      \"name\": \"" + escapeJson(func.getName()) + "\",");
                writer.println("      \"address\": \"" + func.getEntryPoint() + "\",");
                writer.println("      \"size\": " + func.getBody().getNumAddresses() + ",");
                writer.println("      \"signature\": \"" + escapeJson(func.getPrototypeString(false, false)) + "\",");
                writer.println("      \"returnType\": \"" + escapeJson(func.getReturnType().getDisplayName()) + "\",");
                writer.println("      \"callingConvention\": \"" + escapeJson(func.getCallingConventionName()) + "\",");
                writer.println("      \"isExternal\": " + func.isExternal() + ",");
                writer.println("      \"isThunk\": " + func.isThunk() + ",");
                writer.println("      \"hasVarArgs\": " + func.hasVarArgs() + ",");
                writer.println("      \"sourceType\": \"" + func.getSymbol().getSource() + "\",");

                // Parameters
                writer.print("      \"parameters\": [");
                Parameter[] params = func.getParameters();
                for (int i = 0; i < params.length; i++) {
                    if (i > 0) writer.print(", ");
                    writer.print("{\"name\": \"" + escapeJson(params[i].getName()) + "\", ");
                    writer.print("\"type\": \"" + escapeJson(params[i].getDataType().getDisplayName()) + "\"}");
                }
                writer.println("],");

                // Called functions
                writer.print("      \"calls\": [");
                java.util.Set<Function> called = func.getCalledFunctions(monitor);
                int callIdx = 0;
                for (Function calledFunc : called) {
                    if (callIdx >= 50) break;  // Limit to 50 calls
                    if (callIdx > 0) writer.print(", ");
                    writer.print("\"" + escapeJson(calledFunc.getName()) + "\"");
                    callIdx++;
                }
                writer.println("],");

                // Calling functions
                writer.print("      \"calledBy\": [");
                java.util.Set<Function> callers = func.getCallingFunctions(monitor);
                int callerIdx = 0;
                for (Function caller : callers) {
                    if (callerIdx >= 50) break;  // Limit to 50 callers
                    if (callerIdx > 0) writer.print(", ");
                    writer.print("\"" + escapeJson(caller.getName()) + "\"");
                    callerIdx++;
                }
                writer.println("]");

                writer.print("    }");
                count++;
            }

            writer.println();
            writer.println("  ]");
            writer.println("}");

            println("Exported " + count + " functions");
        }
    }

    private String escapeJson(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
    }
}
