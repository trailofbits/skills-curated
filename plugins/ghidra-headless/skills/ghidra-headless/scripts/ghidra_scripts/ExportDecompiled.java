/* ###
 * Export decompiled C code for all functions
 * @category Export
 */

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;

public class ExportDecompiled extends GhidraScript {

    @Override
    public void run() throws Exception {
        String outputDir = System.getenv("GHIDRA_OUTPUT_DIR");
        if (outputDir == null || outputDir.isEmpty()) {
            outputDir = ".";
        }

        String programName = currentProgram.getName().replaceAll("[^a-zA-Z0-9._-]", "_");
        File outputFile = new File(outputDir, programName + "_decompiled.c");

        println("Decompiling all functions to: " + outputFile.getAbsolutePath());

        DecompInterface decompiler = new DecompInterface();
        DecompileOptions options = new DecompileOptions();
        decompiler.setOptions(options);

        if (!decompiler.openProgram(currentProgram)) {
            printerr("Failed to initialize decompiler: " + decompiler.getLastMessage());
            return;
        }

        try (PrintWriter writer = new PrintWriter(new FileWriter(outputFile))) {
            // Write header
            writer.println("/*");
            writer.println(" * Decompiled from: " + currentProgram.getName());
            writer.println(" * Architecture: " + currentProgram.getLanguage().getProcessor());
            writer.println(" * Compiler: " + currentProgram.getCompilerSpec().getCompilerSpecID());
            writer.println(" */");
            writer.println();

            FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
            int count = 0;
            int failed = 0;

            while (functions.hasNext() && !monitor.isCancelled()) {
                Function func = functions.next();

                // Skip external/thunk functions
                if (func.isExternal() || func.isThunk()) {
                    continue;
                }

                monitor.setMessage("Decompiling: " + func.getName());

                DecompileResults results = decompiler.decompileFunction(func, 30, monitor);

                if (results.decompileCompleted()) {
                    String decompiledCode = results.getDecompiledFunction().getC();
                    writer.println("/* Function: " + func.getName() + " @ " + func.getEntryPoint() + " */");
                    writer.println(decompiledCode);
                    writer.println();
                    count++;
                } else {
                    writer.println("/* FAILED TO DECOMPILE: " + func.getName() + " @ " + func.getEntryPoint() + " */");
                    writer.println("/* Error: " + results.getErrorMessage() + " */");
                    writer.println();
                    failed++;
                }
            }

            println("Decompiled " + count + " functions (" + failed + " failed)");
        } finally {
            decompiler.dispose();
        }
    }
}
