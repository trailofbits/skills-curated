/* ###
 * Export all symbols and their addresses
 * @category Export
 */

import ghidra.app.script.GhidraScript;
import ghidra.program.model.symbol.*;
import ghidra.program.model.listing.*;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;

public class ExportSymbols extends GhidraScript {

    @Override
    public void run() throws Exception {
        String outputDir = System.getenv("GHIDRA_OUTPUT_DIR");
        if (outputDir == null || outputDir.isEmpty()) {
            outputDir = ".";
        }

        String programName = currentProgram.getName().replaceAll("[^a-zA-Z0-9._-]", "_");
        File outputFile = new File(outputDir, programName + "_symbols.json");

        println("Exporting symbols to: " + outputFile.getAbsolutePath());

        SymbolTable symbolTable = currentProgram.getSymbolTable();

        try (PrintWriter writer = new PrintWriter(new FileWriter(outputFile))) {
            writer.println("{");
            writer.println("  \"program\": \"" + escapeJson(currentProgram.getName()) + "\",");

            // Export imports (external functions)
            writer.println("  \"imports\": [");
            boolean first = true;
            int importCount = 0;
            SymbolIterator externalSymbols = symbolTable.getExternalSymbols();
            while (externalSymbols.hasNext() && !monitor.isCancelled()) {
                Symbol sym = externalSymbols.next();
                if (!first) writer.println(",");
                first = false;
                writer.println("    {");
                writer.println("      \"name\": \"" + escapeJson(sym.getName()) + "\",");
                writer.println("      \"address\": \"" + sym.getAddress() + "\",");
                writer.println("      \"namespace\": \"" + escapeJson(sym.getParentNamespace().getName()) + "\",");
                writer.println("      \"type\": \"" + sym.getSymbolType() + "\"");
                writer.print("    }");
                importCount++;
            }
            writer.println();
            writer.println("  ],");

            // Export exports (if any)
            writer.println("  \"exports\": [");
            first = true;
            int exportCount = 0;
            // Functions that are potential exports (entry points or exported)
            FunctionIterator functions = currentProgram.getFunctionManager().getExternalFunctions();
            // Look for functions marked as entry points
            FunctionIterator allFunctions = currentProgram.getFunctionManager().getFunctions(true);
            while (allFunctions.hasNext() && !monitor.isCancelled()) {
                Function func = allFunctions.next();
                // Check if function is at an entry point or has export symbol
                Symbol sym = func.getSymbol();
                if (sym.isExternalEntryPoint() || sym.getSource() == SourceType.IMPORTED) {
                    if (!first) writer.println(",");
                    first = false;
                    writer.println("    {");
                    writer.println("      \"name\": \"" + escapeJson(func.getName()) + "\",");
                    writer.println("      \"address\": \"" + func.getEntryPoint() + "\",");
                    writer.println("      \"signature\": \"" + escapeJson(func.getPrototypeString(false, false)) + "\"");
                    writer.print("    }");
                    exportCount++;
                }
            }
            writer.println();
            writer.println("  ],");

            // Export all labels/symbols
            writer.println("  \"symbols\": [");
            first = true;
            int symbolCount = 0;
            SymbolIterator allSymbols = symbolTable.getAllSymbols(true);
            while (allSymbols.hasNext() && !monitor.isCancelled()) {
                Symbol sym = allSymbols.next();
                // Skip default/dynamic symbols to reduce noise
                if (sym.getSource() == SourceType.DEFAULT) {
                    continue;
                }

                if (!first) writer.println(",");
                first = false;
                writer.println("    {");
                writer.println("      \"name\": \"" + escapeJson(sym.getName()) + "\",");
                writer.println("      \"address\": \"" + sym.getAddress() + "\",");
                writer.println("      \"type\": \"" + sym.getSymbolType() + "\",");
                writer.println("      \"source\": \"" + sym.getSource() + "\",");
                writer.println("      \"namespace\": \"" + escapeJson(sym.getParentNamespace().getName()) + "\",");
                writer.println("      \"primary\": " + sym.isPrimary());
                writer.print("    }");
                symbolCount++;

                // Limit to prevent huge outputs
                if (symbolCount >= 10000) {
                    writer.println(",");
                    writer.println("    {\"_truncated\": true, \"_message\": \"Output truncated at 10000 symbols\"}");
                    break;
                }
            }
            writer.println();
            writer.println("  ],");

            // Summary
            writer.println("  \"summary\": {");
            writer.println("    \"imports\": " + importCount + ",");
            writer.println("    \"exports\": " + exportCount + ",");
            writer.println("    \"symbols\": " + symbolCount);
            writer.println("  }");

            writer.println("}");

            println("Exported " + importCount + " imports, " + exportCount + " exports, " + symbolCount + " symbols");
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
