// ============================================================================
// Program.cs — .NET 8 host for a Python-based RAG pipeline
// ============================================================================
// Uses pythonnet (Python.Runtime) to call Pandas data-processing scripts and
// a simple embedding + Ollama RAG engine, all written in Python.
//
// Supports two modes:
//   1. Single-file mode  (--file)  — GroupBy / filter on one Excel file
//   2. Audit mode        (--audit) — merge two files, calculate productivity
//
// Build & Run:
//   dotnet restore
//   dotnet run -- --file ../SampleData/sales.xlsx --group Category --query "Which category has the highest revenue?"
//   dotnet run -- --audit --staff ../SampleData/staff_list.xlsx --tasks ../SampleData/task_logs.xlsx --query "Who is the least productive?"
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

    /// <summary>
    /// Resolve the PythonScripts directory, trying the build-output-relative
    /// path first, then falling back to a path relative to the cwd.
    /// </summary>
    private static string ResolveScriptsDir()
    {
        string candidate = Path.GetFullPath(
            Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "PythonScripts"));
        if (Directory.Exists(candidate))
            return candidate;

        // Fallback: relative to cwd (e.g. inside Docker)
        candidate = Path.GetFullPath("PythonScripts");
        if (Directory.Exists(candidate))
            return candidate;

        throw new DirectoryNotFoundException(
            "Cannot find PythonScripts directory. Run from the project root or set the working directory.");
    }

    // --------------------------------------------------------------------- //
    //  Entry point                                                            //
    // --------------------------------------------------------------------- //

    public static int Main(string[] args)
    {
        // ---- parse CLI args ------------------------------------------------
        var opts = ParseArgs(args);
        if (opts is null) return 1;

        var parsed = opts.Value;

        // ---- decide which mode to run --------------------------------------
        if (parsed.auditMode)
            return RunAuditMode(parsed);
        else
            return RunSingleFileMode(parsed);
    }

    // --------------------------------------------------------------------- //
    //  Python engine bootstrap (shared by both modes)                         //
    // --------------------------------------------------------------------- //

    /// <summary>
    /// Initialise pythonnet: set the DLL path, start the engine, and add
    /// our PythonScripts directory to sys.path.
    /// Returns the scripts directory path for logging.
    /// </summary>
    private static string InitialisePython()
    {
        Runtime.PythonDLL = ResolvePythonDll();
        string scriptsDir = ResolveScriptsDir();

        PythonEngine.Initialize();

        using (Py.GIL())
        {
            dynamic sys = Py.Import("sys");
            sys.path.append(scriptsDir);
        }

        return scriptsDir;
    }

    // --------------------------------------------------------------------- //
    //  Mode 1: Single-file (original behaviour — GroupBy / filter)            //
    // --------------------------------------------------------------------- //

    private static int RunSingleFileMode(ParsedArgs p)
    {
        string fullExcelPath = Path.GetFullPath(p.file!);
        if (!File.Exists(fullExcelPath))
        {
            Console.Error.WriteLine($"[ERROR] Excel file not found: {fullExcelPath}");
            return 1;
        }

        string scriptsDir;
        try { scriptsDir = InitialisePython(); }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"[ERROR] Python init failed: {ex.Message}");
            return 1;
        }

        Console.WriteLine($"[INFO] Python DLL   : {Runtime.PythonDLL}");
        Console.WriteLine($"[INFO] Scripts dir  : {scriptsDir}");
        Console.WriteLine($"[INFO] Excel file   : {fullExcelPath}");
        Console.WriteLine();

        using (Py.GIL())
        {
            try
            {
                Console.WriteLine("=== Step 1: Retrieving data context via Pandas ===");
                dynamic dataProcessor = Py.Import("data_processor");

                string schema = dataProcessor.get_schema(fullExcelPath).ToString();
                Console.WriteLine(schema);
                Console.WriteLine();

                string context;
                if (!string.IsNullOrEmpty(p.groupCol))
                {
                    Console.WriteLine($"Grouping by: {p.groupCol}");
                    context = dataProcessor.summarize_by_column(fullExcelPath, p.groupCol).ToString();
                }
                else if (!string.IsNullOrEmpty(p.filterCol) && !string.IsNullOrEmpty(p.filterVal))
                {
                    Console.WriteLine($"Filtering: {p.filterCol} == {p.filterVal}");
                    context = dataProcessor.filter_rows(fullExcelPath, p.filterCol, p.filterVal).ToString();
                }
                else
                {
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

                if (!string.IsNullOrEmpty(p.query))
                {
                    Console.WriteLine("=== Step 2: RAG — Embedding + LLM ===");
                    Console.WriteLine($"Query : {p.query}");
                    Console.WriteLine($"Model : {p.model}");
                    Console.WriteLine();

                    dynamic ragEngine = Py.Import("rag_engine");
                    string answer = ragEngine.ask(p.query, context, p.model).ToString();

                    Console.WriteLine("--- Answer ---");
                    Console.WriteLine(answer);
                }
                else
                {
                    Console.WriteLine("[INFO] No --query provided; skipping LLM step.");
                }
            }
            catch (PythonException pyEx)
            {
                Console.Error.WriteLine($"[PYTHON ERROR] {pyEx.Message}");
                Console.Error.WriteLine(pyEx.StackTrace);
                return 1;
            }
        }

        PythonEngine.Shutdown();
        Console.WriteLine();
        Console.WriteLine("[INFO] Done.");
        return 0;
    }

    // --------------------------------------------------------------------- //
    //  Mode 2: Audit mode (two-file merge + productivity metrics)             //
    // --------------------------------------------------------------------- //

    private static int RunAuditMode(ParsedArgs p)
    {
        // Validate both files exist
        string staffPath = Path.GetFullPath(p.staffFile!);
        string tasksPath = Path.GetFullPath(p.tasksFile!);

        if (!File.Exists(staffPath))
        {
            Console.Error.WriteLine($"[ERROR] Staff file not found: {staffPath}");
            return 1;
        }
        if (!File.Exists(tasksPath))
        {
            Console.Error.WriteLine($"[ERROR] Tasks file not found: {tasksPath}");
            return 1;
        }

        string scriptsDir;
        try { scriptsDir = InitialisePython(); }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"[ERROR] Python init failed: {ex.Message}");
            return 1;
        }

        Console.WriteLine($"[INFO] Python DLL   : {Runtime.PythonDLL}");
        Console.WriteLine($"[INFO] Scripts dir  : {scriptsDir}");
        Console.WriteLine($"[INFO] Staff file   : {staffPath}");
        Console.WriteLine($"[INFO] Tasks file   : {tasksPath}");
        Console.WriteLine($"[INFO] Merge key    : {p.mergeKey}");
        Console.WriteLine();

        using (Py.GIL())
        {
            try
            {
                string context = GetAuditContext(staffPath, tasksPath, p.mergeKey);

                Console.WriteLine("--- Productivity Report ---");
                Console.WriteLine(context);
                Console.WriteLine();

                if (!string.IsNullOrEmpty(p.query))
                {
                    string answer = GetAIResponse(p.query, staffPath, tasksPath, p.mergeKey, p.model);
                    Console.WriteLine("--- AI Auditor Answer ---");
                    Console.WriteLine(answer);
                }
                else
                {
                    Console.WriteLine("[INFO] No --query provided; skipping LLM step.");
                    Console.WriteLine("       The productivity report above can be used as RAG context.");
                }
            }
            catch (PythonException pyEx)
            {
                Console.Error.WriteLine($"[PYTHON ERROR] {pyEx.Message}");
                Console.Error.WriteLine(pyEx.StackTrace);
                return 1;
            }
        }

        PythonEngine.Shutdown();
        Console.WriteLine();
        Console.WriteLine("[INFO] Done.");
        return 0;
    }

    // --------------------------------------------------------------------- //
    //  GetAuditContext — call analysis_engine.build_audit_context             //
    // --------------------------------------------------------------------- //

    /// <summary>
    /// Call the Python analysis_engine to merge two files and produce
    /// a Markdown productivity report.  Must be called inside a GIL block.
    /// </summary>
    private static string GetAuditContext(
        string staffPath, string tasksPath, string mergeKey)
    {
        Console.WriteLine("=== Step 1: Building Productivity Context (Pandas merge + metrics) ===");
        dynamic analysisEngine = Py.Import("analysis_engine");

        string schema = analysisEngine.get_merged_schema(staffPath, tasksPath, mergeKey).ToString();
        Console.WriteLine(schema);
        Console.WriteLine();

        string context = analysisEngine.build_audit_context(
            staffPath, tasksPath, mergeKey).ToString();
        return context;
    }

    // --------------------------------------------------------------------- //
    //  GetAIResponse — end-to-end: context + RAG + LLM answer                //
    // --------------------------------------------------------------------- //

    /// <summary>
    /// High-level method that C# code calls to get a natural-language answer
    /// from the Office Auditor RAG pipeline.
    ///
    /// 1. Calls analysis_engine.build_audit_context() to merge the two files
    ///    and calculate productivity metrics via Pandas.
    /// 2. Passes the resulting Markdown context + user query to the RAG engine
    ///    with the Office Auditor system prompt.
    /// 3. Returns the LLM's answer as a string.
    ///
    /// Must be called inside a Py.GIL() block.
    /// </summary>
    public static string GetAIResponse(
        string userQuery,
        string file1Path,
        string file2Path,
        string mergeKey = "EmployeeID",
        string ollamaModel = "llama3")
    {
        // Step 1: Build productivity context from the two files
        dynamic analysisEngine = Py.Import("analysis_engine");
        string context = analysisEngine.build_audit_context(
            file1Path, file2Path, mergeKey).ToString();

        // Step 2: Send context + query through the auditor RAG pipeline
        Console.WriteLine("=== Step 2: Office Auditor RAG — Embedding + LLM ===");
        Console.WriteLine($"Query : {userQuery}");
        Console.WriteLine($"Model : {ollamaModel}");
        Console.WriteLine();

        dynamic ragEngine = Py.Import("rag_engine");
        string answer = ragEngine.ask_auditor(userQuery, context, ollamaModel).ToString();
        return answer;
    }

    // --------------------------------------------------------------------- //
    //  Argument parsing                                                       //
    // --------------------------------------------------------------------- //

    private record struct ParsedArgs(
        // Single-file mode
        string? file,
        string? groupCol,
        string? filterCol,
        string? filterVal,
        // Audit mode
        bool auditMode,
        string? staffFile,
        string? tasksFile,
        string mergeKey,
        // Shared
        string? query,
        string model);

    private static ParsedArgs? ParseArgs(string[] args)
    {
        string? file = null, group = null, filterCol = null, filterVal = null;
        string? staffFile = null, tasksFile = null;
        string mergeKey = "EmployeeID";
        bool auditMode = false;
        string? query = null;
        string model = "llama3";

        for (int i = 0; i < args.Length; i++)
        {
            switch (args[i])
            {
                // -- single-file mode --
                case "--file" or "-f":
                    file = args[++i]; break;
                case "--group" or "-g":
                    group = args[++i]; break;
                case "--filter-column":
                    filterCol = args[++i]; break;
                case "--filter-value":
                    filterVal = args[++i]; break;

                // -- audit mode --
                case "--audit":
                    auditMode = true; break;
                case "--staff":
                    staffFile = args[++i]; break;
                case "--tasks":
                    tasksFile = args[++i]; break;
                case "--merge-key":
                    mergeKey = args[++i]; break;

                // -- shared --
                case "--query" or "-q":
                    query = args[++i]; break;
                case "--model" or "-m":
                    model = args[++i]; break;
                case "--help" or "-h":
                    PrintUsage(); return null;
            }
        }

        // Validate required args
        if (auditMode)
        {
            if (string.IsNullOrEmpty(staffFile) || string.IsNullOrEmpty(tasksFile))
            {
                Console.Error.WriteLine("[ERROR] Audit mode requires --staff and --tasks.");
                PrintUsage();
                return null;
            }
        }
        else
        {
            if (string.IsNullOrEmpty(file))
            {
                Console.Error.WriteLine("[ERROR] --file is required (or use --audit mode).");
                PrintUsage();
                return null;
            }
        }

        return new ParsedArgs(file, group, filterCol, filterVal,
                              auditMode, staffFile, tasksFile, mergeKey,
                              query, model);
    }

    private static void PrintUsage()
    {
        Console.WriteLine(@"
Usage: RagHost [options]

SINGLE-FILE MODE (GroupBy / Filter):
  --file, -f <path>          Path to the Excel (.xlsx) file  [required]
  --group, -g <column>       Column to GroupBy for summarization
  --filter-column <column>   Column to filter on
  --filter-value <value>     Value to match in the filter column

AUDIT MODE (Two-file merge + productivity analysis):
  --audit                    Enable audit mode
  --staff <path>             Path to the staff list file (.xlsx/.csv)  [required]
  --tasks <path>             Path to the task logs file (.xlsx/.csv)   [required]
  --merge-key <column>       Column to join on (default: EmployeeID)

SHARED OPTIONS:
  --query, -q <question>     Natural-language question for the RAG pipeline
  --model, -m <name>         Ollama model name (default: llama3)
  --help, -h                 Show this help message

Examples:
  Single-file:
    dotnet run -- --file sales.xlsx --group Category
    dotnet run -- --file sales.xlsx -g Category -q ""Which category sells the most?""

  Audit mode:
    dotnet run -- --audit --staff staff_list.xlsx --tasks task_logs.xlsx
    dotnet run -- --audit --staff staff.xlsx --tasks logs.xlsx -q ""Who is least productive?""
    dotnet run -- --audit --staff staff.xlsx --tasks logs.xlsx --merge-key EmpID -q ""Trends?""
");
    }
}
