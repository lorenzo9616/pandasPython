// ============================================================================
// Program.cs — .NET 8 host for a Python-based RAG pipeline
// ============================================================================
// Uses pythonnet (Python.Runtime) to call Pandas data-processing scripts and
// a simple embedding + Ollama RAG engine, all written in Python.
//
// Build & Run:
//   dotnet restore
//   dotnet run -- --file ../SampleData/sales.xlsx --group Category --query "Which category has the highest revenue?"
// ============================================================================

using System;
using System.IO;
using System.Runtime.InteropServices;
using Python.Runtime;

namespace RagHost;

public static class Program
{
    // --------------------------------------------------------------------- //
    //  Configuration — adjust to match your local Python installation         //
    // --------------------------------------------------------------------- //

    /// <summary>
    /// Resolve the Python shared library (e.g. python3.11.dll / libpython3.11.so).
    /// Set the PYTHON_DLL environment variable to override auto-detection.
    /// </summary>
    private static string ResolvePythonDll()
    {
        string? envDll = Environment.GetEnvironmentVariable("PYTHON_DLL");
        if (!string.IsNullOrEmpty(envDll))
        {
            if (!File.Exists(envDll))
                throw new FileNotFoundException(
                    $"PYTHON_DLL points to a missing file: {envDll}");
            return envDll;
        }

        // Sensible defaults per platform
        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            return "python311.dll";      // must be on PATH
        if (RuntimeInformation.IsOSPlatform(OSPlatform.Linux))
            return "libpython3.11.so";   // adjust version as needed
        if (RuntimeInformation.IsOSPlatform(OSPlatform.OSX))
            return "libpython3.11.dylib";

        throw new PlatformNotSupportedException("Unsupported OS platform.");
    }

    // --------------------------------------------------------------------- //
    //  Entry point                                                            //
    // --------------------------------------------------------------------- //

    public static int Main(string[] args)
    {
        // ---- parse CLI args ------------------------------------------------
        var opts = ParseArgs(args);
        if (opts is null) return 1;

        var (excelPath, groupColumn, filterColumn, filterValue, query, ollamaModel) = opts.Value;

        // ---- verify file exists --------------------------------------------
        string fullExcelPath = Path.GetFullPath(excelPath);
        if (!File.Exists(fullExcelPath))
        {
            Console.Error.WriteLine($"[ERROR] Excel file not found: {fullExcelPath}");
            return 1;
        }

        // ---- configure pythonnet -------------------------------------------
        try
        {
            Runtime.PythonDLL = ResolvePythonDll();
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"[ERROR] Python DLL resolution failed: {ex.Message}");
            Console.Error.WriteLine("  Hint: set the PYTHON_DLL environment variable to the full path of your Python shared library.");
            return 1;
        }

        // Point pythonnet at our PythonScripts directory so `import data_processor` works.
        string scriptsDir = Path.GetFullPath(
            Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "PythonScripts"));
        if (!Directory.Exists(scriptsDir))
        {
            // Fallback: relative to cwd
            scriptsDir = Path.GetFullPath("PythonScripts");
        }

        Console.WriteLine($"[INFO] Python DLL   : {Runtime.PythonDLL}");
        Console.WriteLine($"[INFO] Scripts dir  : {scriptsDir}");
        Console.WriteLine($"[INFO] Excel file   : {fullExcelPath}");
        Console.WriteLine();

        // ---- initialise the Python engine ----------------------------------
        PythonEngine.Initialize();

        // All interaction with Python MUST happen inside a GIL block.
        // Py.GIL() acquires the Global Interpreter Lock and releases it
        // when the using-block exits (via IDisposable).
        using (Py.GIL())
        {
            // Add our scripts folder to sys.path
            dynamic sys = Py.Import("sys");
            sys.path.append(scriptsDir);

            try
            {
                // ---- Step 1: Retrieve data context via Pandas ---------------
                Console.WriteLine("=== Step 1: Retrieving data context via Pandas ===");
                dynamic dataProcessor = Py.Import("data_processor");

                // Print schema first
                string schema = dataProcessor.get_schema(fullExcelPath).ToString();
                Console.WriteLine(schema);
                Console.WriteLine();

                string context;
                if (!string.IsNullOrEmpty(groupColumn))
                {
                    Console.WriteLine($"Grouping by: {groupColumn}");
                    context = dataProcessor.summarize_by_column(fullExcelPath, groupColumn).ToString();
                }
                else if (!string.IsNullOrEmpty(filterColumn) && !string.IsNullOrEmpty(filterValue))
                {
                    Console.WriteLine($"Filtering: {filterColumn} == {filterValue}");
                    context = dataProcessor.filter_rows(fullExcelPath, filterColumn, filterValue).ToString();
                }
                else
                {
                    // Default: summarize by the first non-numeric column
                    dynamic pd = Py.Import("pandas");
                    dynamic df = pd.read_excel(fullExcelPath, engine: "openpyxl");
                    string firstCol = df.columns.__getitem__(0).ToString();
                    Console.WriteLine($"Auto-grouping by first column: {firstCol}");
                    context = dataProcessor.summarize_by_column(fullExcelPath, firstCol).ToString();
                }

                Console.WriteLine();
                Console.WriteLine("--- Retrieved Context ---");
                Console.WriteLine(context);
                Console.WriteLine();

                // ---- Step 2: RAG — embed, retrieve, prompt, answer ----------
                if (!string.IsNullOrEmpty(query))
                {
                    Console.WriteLine("=== Step 2: RAG — Embedding + LLM ===");
                    Console.WriteLine($"Query : {query}");
                    Console.WriteLine($"Model : {ollamaModel}");
                    Console.WriteLine();

                    dynamic ragEngine = Py.Import("rag_engine");
                    string answer = ragEngine.ask(query, context, ollamaModel).ToString();

                    Console.WriteLine("--- Answer ---");
                    Console.WriteLine(answer);
                }
                else
                {
                    Console.WriteLine("[INFO] No --query provided; skipping LLM step.");
                    Console.WriteLine("       The retrieved context above can be used as RAG input.");
                }
            }
            catch (PythonException pyEx)
            {
                Console.Error.WriteLine($"[PYTHON ERROR] {pyEx.Message}");
                Console.Error.WriteLine(pyEx.StackTrace);
                return 1;
            }
        }

        // Shutdown must happen OUTSIDE the GIL block.
        PythonEngine.Shutdown();

        Console.WriteLine();
        Console.WriteLine("[INFO] Done.");
        return 0;
    }

    // --------------------------------------------------------------------- //
    //  Argument parsing                                                       //
    // --------------------------------------------------------------------- //

    private static (string excelPath, string? groupCol, string? filterCol,
                     string? filterVal, string? query, string ollamaModel)?
        ParseArgs(string[] args)
    {
        string? file = null, group = null, filterCol = null, filterVal = null;
        string? query = null;
        string model = "llama3";

        for (int i = 0; i < args.Length; i++)
        {
            switch (args[i])
            {
                case "--file" or "-f":
                    file = args[++i]; break;
                case "--group" or "-g":
                    group = args[++i]; break;
                case "--filter-column":
                    filterCol = args[++i]; break;
                case "--filter-value":
                    filterVal = args[++i]; break;
                case "--query" or "-q":
                    query = args[++i]; break;
                case "--model" or "-m":
                    model = args[++i]; break;
                case "--help" or "-h":
                    PrintUsage(); return null;
            }
        }

        if (string.IsNullOrEmpty(file))
        {
            Console.Error.WriteLine("[ERROR] --file is required.");
            PrintUsage();
            return null;
        }

        return (file, group, filterCol, filterVal, query, model);
    }

    private static void PrintUsage()
    {
        Console.WriteLine(@"
Usage: RagHost [options]

Options:
  --file, -f <path>          Path to the Excel (.xlsx) file  [required]
  --group, -g <column>       Column to GroupBy for summarization
  --filter-column <column>   Column to filter on
  --filter-value <value>     Value to match in the filter column
  --query, -q <question>     Natural-language question for the RAG pipeline
  --model, -m <name>         Ollama model name (default: llama3)
  --help, -h                 Show this help message

Examples:
  dotnet run -- --file sales.xlsx --group Category
  dotnet run -- --file sales.xlsx --filter-column Region --filter-value North
  dotnet run -- --file sales.xlsx -g Category -q ""Which category sells the most?""
");
    }
}
