# =============================================================================
# Multi-stage Dockerfile: .NET 8 + Python 3.11 RAG System
# =============================================================================
# Stage 1: Build the C# application
# Stage 2: Runtime with both .NET and Python
# =============================================================================

# ---------- Stage 1: Build ----------
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build

WORKDIR /src
COPY RagHost.sln ./
COPY RagHost/RagHost.csproj RagHost/
RUN dotnet restore

COPY RagHost/ RagHost/
RUN dotnet publish RagHost/RagHost.csproj -c Release -o /app/publish --no-restore

# ---------- Stage 2: Runtime ----------
FROM mcr.microsoft.com/dotnet/runtime:8.0 AS runtime

# Install Python 3.11 + pip into the .NET runtime image
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.11 \
        python3.11-dev \
        python3.11-venv \
        python3-pip \
        libpython3.11 \
    && rm -rf /var/lib/apt/lists/*

# Make python3.11 the default python/python3
RUN update-alternatives --install /usr/bin/python  python  /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

WORKDIR /app

# Install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Copy the published .NET app
COPY --from=build /app/publish .

# Copy Python scripts and sample data
COPY PythonScripts/ /app/PythonScripts/
COPY SampleData/ /app/SampleData/

# Generate all sample Excel data
RUN cd /app/SampleData && python generate_sample.py && python generate_audit_data.py && python generate_compare_data.py

# Set the Python shared library path for pythonnet
ENV PYTHON_DLL=/usr/lib/x86_64-linux-gnu/libpython3.11.so
ENV DOTNET_EnableDiagnostics=0

# Default: show help
ENTRYPOINT ["dotnet", "RagHost.dll"]
CMD ["--help"]
