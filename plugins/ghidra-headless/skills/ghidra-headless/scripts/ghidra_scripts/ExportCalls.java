/* ###
 * Export function call graph
 * @category Export
 */

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.*;

public class ExportCalls extends GhidraScript {

    @Override
    public void run() throws Exception {
        String outputDir = System.getenv("GHIDRA_OUTPUT_DIR");
        if (outputDir == null || outputDir.isEmpty()) {
            outputDir = ".";
        }

        String programName = currentProgram.getName().replaceAll("[^a-zA-Z0-9._-]", "_");
        File outputFile = new File(outputDir, programName + "_calls.json");

        println("Exporting call graph to: " + outputFile.getAbsolutePath());

        // Build call graph
        Map<String, Set<String>> callGraph = new LinkedHashMap<>();
        Map<String, String> functionAddresses = new LinkedHashMap<>();

        FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);

        while (functions.hasNext() && !monitor.isCancelled()) {
            Function func = functions.next();
            String funcName = func.getName();
            functionAddresses.put(funcName, func.getEntryPoint().toString());

            Set<String> calls = new TreeSet<>();
            Set<Function> calledFunctions = func.getCalledFunctions(monitor);

            for (Function called : calledFunctions) {
                calls.add(called.getName());
            }

            callGraph.put(funcName, calls);
        }

        // Write output
        try (PrintWriter writer = new PrintWriter(new FileWriter(outputFile))) {
            writer.println("{");
            writer.println("  \"program\": \"" + escapeJson(currentProgram.getName()) + "\",");
            writer.println("  \"totalFunctions\": " + callGraph.size() + ",");
            writer.println("  \"callGraph\": {");

            boolean firstFunc = true;
            for (Map.Entry<String, Set<String>> entry : callGraph.entrySet()) {
                if (!firstFunc) {
                    writer.println(",");
                }
                firstFunc = false;

                String funcName = entry.getKey();
                Set<String> calls = entry.getValue();

                writer.print("    \"" + escapeJson(funcName) + "\": {");
                writer.print("\"address\": \"" + functionAddresses.get(funcName) + "\", ");
                writer.print("\"calls\": [");

                boolean firstCall = true;
                for (String call : calls) {
                    if (!firstCall) {
                        writer.print(", ");
                    }
                    firstCall = false;
                    writer.print("\"" + escapeJson(call) + "\"");
                }

                writer.print("]}");
            }

            writer.println();
            writer.println("  },");

            // Also export interesting functions (potential entry points, etc.)
            writer.println("  \"interestingFunctions\": {");

            // Find functions with no callers (potential entry points)
            Set<String> noCaller = new TreeSet<>();
            Set<String> allCalled = new TreeSet<>();
            for (Set<String> calls : callGraph.values()) {
                allCalled.addAll(calls);
            }
            for (String func : callGraph.keySet()) {
                if (!allCalled.contains(func)) {
                    noCaller.add(func);
                }
            }

            writer.print("    \"potentialEntryPoints\": [");
            boolean first = true;
            for (String func : noCaller) {
                if (!first) writer.print(", ");
                first = false;
                writer.print("\"" + escapeJson(func) + "\"");
            }
            writer.println("],");

            // Find functions with many callers (commonly used)
            Map<String, Integer> callerCount = new HashMap<>();
            for (Set<String> calls : callGraph.values()) {
                for (String call : calls) {
                    callerCount.merge(call, 1, Integer::sum);
                }
            }

            List<Map.Entry<String, Integer>> sorted = new ArrayList<>(callerCount.entrySet());
            sorted.sort((a, b) -> b.getValue().compareTo(a.getValue()));

            writer.print("    \"mostCalled\": [");
            first = true;
            for (int i = 0; i < Math.min(20, sorted.size()); i++) {
                if (!first) writer.print(", ");
                first = false;
                Map.Entry<String, Integer> e = sorted.get(i);
                writer.print("{\"name\": \"" + escapeJson(e.getKey()) + "\", \"count\": " + e.getValue() + "}");
            }
            writer.println("]");

            writer.println("  }");
            writer.println("}");

            println("Exported call graph with " + callGraph.size() + " functions");
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
