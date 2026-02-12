/* ###
 * Export comprehensive analysis: decompiled code, functions, strings, calls, and symbols
 * @category Export
 */

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.data.DataType;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.*;

public class ExportAll extends GhidraScript {

    private String outputDir;
    private String programName;

    @Override
    public void run() throws Exception {
        outputDir = System.getenv("GHIDRA_OUTPUT_DIR");
        if (outputDir == null || outputDir.isEmpty()) {
            outputDir = ".";
        }

        programName = currentProgram.getName().replaceAll("[^a-zA-Z0-9._-]", "_");

        println("=== Starting comprehensive export ===");
        println("Output directory: " + outputDir);
        println("Program: " + currentProgram.getName());
        println("Architecture: " + currentProgram.getLanguage().getProcessor());
        println("");

        // Export summary first
        exportSummary();

        // Export decompiled code
        exportDecompiled();

        // Export functions
        exportFunctions();

        // Export strings
        exportStrings();

        // Export interesting patterns
        exportInteresting();

        println("");
        println("=== Export complete ===");
    }

    private void exportSummary() throws Exception {
        File outputFile = new File(outputDir, programName + "_summary.txt");
        println("Exporting summary to: " + outputFile.getName());

        try (PrintWriter writer = new PrintWriter(new FileWriter(outputFile))) {
            writer.println("Binary Analysis Summary");
            writer.println("=======================");
            writer.println("");
            writer.println("File: " + currentProgram.getName());
            writer.println("Architecture: " + currentProgram.getLanguage().getProcessor());
            writer.println("Address Size: " + currentProgram.getLanguage().getLanguageDescription().getSize() + " bit");
            writer.println("Endianness: " + currentProgram.getLanguage().isBigEndian() + " (big endian)");
            writer.println("Compiler: " + currentProgram.getCompilerSpec().getCompilerSpecID());
            writer.println("");

            // Count functions
            int totalFuncs = 0, externalFuncs = 0, thunkFuncs = 0;
            FunctionIterator funcs = currentProgram.getFunctionManager().getFunctions(true);
            while (funcs.hasNext()) {
                Function f = funcs.next();
                totalFuncs++;
                if (f.isExternal()) externalFuncs++;
                if (f.isThunk()) thunkFuncs++;
            }

            writer.println("Functions:");
            writer.println("  Total: " + totalFuncs);
            writer.println("  External: " + externalFuncs);
            writer.println("  Thunks: " + thunkFuncs);
            writer.println("  User-defined: " + (totalFuncs - externalFuncs - thunkFuncs));
            writer.println("");

            // Memory sections
            writer.println("Memory Sections:");
            for (var block : currentProgram.getMemory().getBlocks()) {
                writer.println("  " + block.getName() + ": " + block.getStart() + " - " + block.getEnd() +
                    " (" + block.getSize() + " bytes)" +
                    (block.isExecute() ? " [X]" : "") +
                    (block.isWrite() ? " [W]" : "") +
                    (block.isRead() ? " [R]" : ""));
            }
        }
    }

    private void exportDecompiled() throws Exception {
        File outputFile = new File(outputDir, programName + "_decompiled.c");
        println("Exporting decompiled code to: " + outputFile.getName());

        DecompInterface decompiler = new DecompInterface();
        DecompileOptions options = new DecompileOptions();
        decompiler.setOptions(options);

        if (!decompiler.openProgram(currentProgram)) {
            printerr("Failed to initialize decompiler");
            return;
        }

        try (PrintWriter writer = new PrintWriter(new FileWriter(outputFile))) {
            writer.println("/* Decompiled from: " + currentProgram.getName() + " */");
            writer.println("");

            FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
            int count = 0;

            while (functions.hasNext() && !monitor.isCancelled()) {
                Function func = functions.next();
                if (func.isExternal() || func.isThunk()) continue;

                DecompileResults results = decompiler.decompileFunction(func, 30, monitor);
                if (results.decompileCompleted()) {
                    writer.println("/* " + func.getName() + " @ " + func.getEntryPoint() + " */");
                    writer.println(results.getDecompiledFunction().getC());
                    writer.println("");
                    count++;
                }
            }
            println("  Decompiled " + count + " functions");
        } finally {
            decompiler.dispose();
        }
    }

    private void exportFunctions() throws Exception {
        File outputFile = new File(outputDir, programName + "_functions.json");
        println("Exporting functions to: " + outputFile.getName());

        try (PrintWriter writer = new PrintWriter(new FileWriter(outputFile))) {
            writer.println("[");

            FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
            boolean first = true;
            int count = 0;

            while (functions.hasNext() && !monitor.isCancelled()) {
                Function func = functions.next();
                if (!first) writer.println(",");
                first = false;

                writer.println("  {");
                writer.println("    \"name\": \"" + escapeJson(func.getName()) + "\",");
                writer.println("    \"address\": \"" + func.getEntryPoint() + "\",");
                writer.println("    \"signature\": \"" + escapeJson(func.getPrototypeString(false, false)) + "\",");
                writer.println("    \"external\": " + func.isExternal() + ",");

                // Get calls
                java.util.Set<Function> calls = func.getCalledFunctions(monitor);
                writer.print("    \"calls\": [");
                int callIdx = 0;
                for (Function calledFunc : calls) {
                    if (callIdx >= 20) break;
                    if (callIdx > 0) writer.print(", ");
                    writer.print("\"" + escapeJson(calledFunc.getName()) + "\"");
                    callIdx++;
                }
                writer.println("]");
                writer.print("  }");
                count++;
            }

            writer.println();
            writer.println("]");
            println("  Exported " + count + " functions");
        }
    }

    private void exportStrings() throws Exception {
        File outputFile = new File(outputDir, programName + "_strings.txt");
        println("Exporting strings to: " + outputFile.getName());

        try (PrintWriter writer = new PrintWriter(new FileWriter(outputFile))) {
            DataIterator dataIterator = currentProgram.getListing().getDefinedData(true);
            int count = 0;

            while (dataIterator.hasNext() && !monitor.isCancelled()) {
                Data data = dataIterator.next();
                DataType dt = data.getBaseDataType();
                String typeName = dt.getName().toLowerCase();

                if (typeName.contains("string") || typeName.contains("unicode")) {
                    Object value = data.getValue();
                    if (value instanceof String) {
                        String str = (String) value;
                        if (str.length() >= 4) {
                            writer.println(data.getAddress() + ": " + str);
                            count++;
                        }
                    }
                }
            }
            println("  Exported " + count + " strings");
        }
    }

    private void exportInteresting() throws Exception {
        File outputFile = new File(outputDir, programName + "_interesting.txt");
        println("Analyzing interesting patterns...");

        // Interesting function name patterns
        String[] interestingPatterns = {
            "crypt", "encrypt", "decrypt", "aes", "des", "rsa", "md5", "sha",
            "password", "passwd", "secret", "key", "token", "auth",
            "socket", "connect", "send", "recv", "http", "url", "dns",
            "file", "open", "read", "write", "exec", "system", "shell", "cmd",
            "malloc", "free", "alloc", "memcpy", "strcpy", "sprintf",
            "debug", "log", "print", "error", "fail"
        };

        try (PrintWriter writer = new PrintWriter(new FileWriter(outputFile))) {
            writer.println("Interesting Functions and Patterns");
            writer.println("===================================");
            writer.println("");

            // Find functions matching patterns
            Map<String, List<String>> categorized = new LinkedHashMap<>();
            for (String pattern : interestingPatterns) {
                categorized.put(pattern, new ArrayList<>());
            }

            FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
            while (functions.hasNext()) {
                Function func = functions.next();
                String name = func.getName().toLowerCase();
                for (String pattern : interestingPatterns) {
                    if (name.contains(pattern)) {
                        categorized.get(pattern).add(func.getName() + " @ " + func.getEntryPoint());
                    }
                }
            }

            for (Map.Entry<String, List<String>> entry : categorized.entrySet()) {
                if (!entry.getValue().isEmpty()) {
                    writer.println("[" + entry.getKey().toUpperCase() + " related]");
                    for (String func : entry.getValue()) {
                        writer.println("  " + func);
                    }
                    writer.println("");
                }
            }

            // Find potential vulnerabilities (dangerous function calls)
            writer.println("[POTENTIALLY DANGEROUS FUNCTIONS]");
            String[] dangerous = {"strcpy", "sprintf", "gets", "scanf", "strcat", "system", "exec"};
            for (String pattern : dangerous) {
                SymbolIterator symbols = currentProgram.getSymbolTable().getSymbols(pattern);
                while (symbols.hasNext()) {
                    Symbol sym = symbols.next();
                    writer.println("  " + sym.getName() + " @ " + sym.getAddress());
                }
            }
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
