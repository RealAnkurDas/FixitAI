# FixitAI Modules

This directory contains the core search tools and utilities that power the FixitAI multi-agent system. The modules are organized into functional tools and test utilities.

## 🔧 Core Search Tools

### **External Data Source Tools**
- **`reddit_tool.py`**: Reddit post search using Google PSE API
- **`medium_tool.py`**: Medium article search using Google PSE API  
- **`wikihow_tool.py`**: WikiHow guide search with content extraction
- **`ifixit_tool.py`**: iFixit repair guide search via API and web scraping
- **`stackexchange_tool.py`**: StackExchange Q&A search using official API
- **`manualslib_tool.py`**: ManualsLib manual search with web scraping
- **`tavily_tool.py`**: Tavily AI-powered web search integration

### **Local Services**
- **`googlemaps_tool.py`**: Google Maps Places API for local repair shop discovery
- **`local_repair_tool.py`**: Local repair shop search coordination with LLM query generation
- **`upcycleideas_tool.py`**: Creative upcycling idea generation using LLM

### **Core Utilities**
- **`local_user_storage.py`**: User-specific query storage and management
- **`user_query_service.py`**: Query processing and context management

## 🧪 Test Modules (modules_test/)

The `modules_test/` directory contains actual test files for system validation:

### **Connectivity Tests**
- **`test_llm_connectivity.py`**: LLM connection and functionality testing
- **`test_mock_agents.py`**: Mock agent implementations for testing
- **`test_repair_manuals.py`**: Comprehensive repair manual search testing
- **`test_manualslib.py`**: Basic ManualsLib functionality testing
- **`run_all_tests.py`**: Master test runner for all components

## 🔧 Available Tools

### 1. **test_llm_connectivity.py**
Tests the ChatOllama LLM connection and basic functionality.
- ✅ Basic LLM connectivity
- ✅ Classification prompt testing
- ✅ Aggregation prompt testing

**Run individually:**
```bash
cd modules
python test_llm_connectivity.py
```

### 2. **test_wikihow.py**
Tests the WikiHow search functionality (self-contained implementation).
- ✅ **Advanced WikiHow scraping** with full article content extraction
- ✅ **Step-by-step content parsing** from individual articles
- ✅ **Metadata extraction** (date, views, title, link)
- ✅ **Structured JSON output** matching your required format
- ✅ **Multiple article processing** with configurable limits

**Run individually:**
```bash
cd modules
python test_wikihow.py
```

### 3. **test_ifixit.py**
Tests the basic iFixit search functionality (self-contained implementation).
- ✅ iFixit search via DuckDuckGo
- ✅ Guide ID extraction
- ✅ URL generation

**Run individually:**
```bash
cd modules
python test_ifixit.py
```

### 4. **test_ifixit_api.py**
Tests the advanced iFixit API functionality (self-contained implementation).
- ✅ Direct iFixit API connectivity
- ✅ Guide details retrieval
- ✅ Tools and steps extraction
- ✅ Parts and difficulty information

**Run individually:**
```bash
cd modules
python test_ifixit_api.py
```

### 5. **test_manualslib.py**
Tests the Manualslib search functionality (self-contained implementation).
- ✅ Manualslib web scraping
- ✅ Manual URL extraction
- ✅ Content parsing

**Run individually:**
```bash
cd modules
python test_manualslib.py
```

### 6. **test_repair_manuals.py**
Tests the comprehensive repair manuals search (self-contained implementation).
- ✅ Device-specific searches
- ✅ Part-specific searches
- ✅ Keyword-based searches
- ✅ iFixit priority search
- ✅ General web search fallback

**Run individually:**
```bash
cd modules
python test_repair_manuals.py
```

### 7. **test_mock_agents.py**
Tests the mock implementations of agents without real APIs.
- ✅ Websearch mock
- ✅ Reddit mock
- ✅ Stack Exchange mock
- ✅ Official support mock
- ✅ Manufacturer manual mock
- ✅ Online retailer mock

**Run individually:**
```bash
cd modules
python test_mock_agents.py
```

## 🚀 Master Test Runner

### **run_all_tests.py**
Comprehensive test runner that tests all components and provides a detailed report.

**Run all tests:**
```bash
cd modules
python run_all_tests.py all
```

**Run specific test:**
```bash
cd modules
python run_all_tests.py llm          # LLM only
python run_all_tests.py wikihow      # WikiHow only
python run_all_tests.py ifixit       # iFixit basic only
python run_all_tests.py ifixit_api   # iFixit API advanced only
python run_all_tests.py manualslib   # Manualslib only
python run_all_tests.py repair_manuals # Repair manuals search only
python run_all_tests.py mock         # Mock agents only
```

## 📊 What Each Test Verifies

### **LLM Test**
- Ollama server connectivity
- Model availability (`qwen2.5vl:7b`)
- Basic prompt/response functionality
- Classification prompt testing
- Aggregation prompt testing

### **API Tests (WikiHow, iFixit, Manualslib)**
- Network connectivity
- API endpoint accessibility
- Response parsing
- URL extraction
- Content formatting

### **Mock Tests**
- Data structure validation
- Metadata generation
- URL formatting
- Error handling simulation

## 🔧 Troubleshooting

### **LLM Issues**
```bash
# Check if Ollama is running
ollama list

# Check Ollama status
ollama serve

# Verify model installation
ollama pull qwen2.5vl:7b
```

### **API Issues**
- Check internet connectivity
- Verify no firewall blocking
- Check if websites are accessible in browser
- Verify `tools.py` dependencies are installed

### **Import Issues**
- Ensure you're running from the `modules` directory
- Check that `tools.py` exists in the parent directory
- Verify Python path includes the parent directory

## 📈 Test Results Interpretation

### **All Tests Pass (5/5)**
🎉 Your system is fully ready! All components are working correctly.

### **Most Tests Pass (3-4/5)**
⚠️ System can run with some limitations. Check failed components.

### **Many Tests Fail (1-2/5)**
❌ System has significant issues. Fix connectivity problems before proceeding.

## 🎯 Recommended Testing Order

1. **Start with LLM test** - This is the core of your system
2. **Test real APIs** - WikiHow, iFixit, Manualslib
3. **Verify mock agents** - Ensure fallback functionality works
4. **Run full system test** - Only after individual components work

## 💡 Usage Tips

- Run tests from the `modules` directory
- Check the detailed output for specific error messages
- Use individual tests to debug specific components
- Use the master runner for comprehensive validation
- Fix connectivity issues before running the full multi-agent system

## 🔗 Dependencies

Make sure these are installed in your main environment:
```bash
pip install requests beautifulsoup4 python-dotenv langchain-ollama langchain langchain-community
```

**Note**: Each test module is now **self-contained** with its own implementation:
- **WikiHow**: Uses DuckDuckGo search via `langchain_community.tools.DuckDuckGoSearchRun`
- **iFixit**: Uses DuckDuckGo search with site-specific filtering
- **iFixit API**: Direct API connectivity with full guide details extraction
- **Manualslib**: Direct web scraping with BeautifulSoup
- **Repair Manuals**: Comprehensive search with iFixit priority + web fallback

No external imports needed - each module can run independently!
