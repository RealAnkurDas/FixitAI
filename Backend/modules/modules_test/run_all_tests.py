#!/usr/bin/env python3
"""
Master test runner for all connectivity modules
Runs tests for each individual component to verify connectivity
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_connectivity_tests():
    """Run all connectivity tests"""
    print("🚀 Running All Connectivity Tests...")
    print("=" * 60)
    
    # Test results tracking
    test_results = {}
    
    # Test 1: LLM Connectivity
    print("\n1️⃣ Testing LLM Connectivity...")
    try:
        from test_llm_connectivity import test_llm_connectivity
        test_llm_connectivity()
        test_results['llm'] = True
        print("   ✅ LLM test completed successfully")
    except Exception as e:
        test_results['llm'] = False
        print(f"   ❌ LLM test failed: {e}")
    
    # Test 2: WikiHow Connectivity
    print("\n2️⃣ Testing WikiHow Connectivity...")
    try:
        from wikihow_tool import test_wikihow_connectivity
        test_wikihow_connectivity()
        test_results['wikihow'] = True
        print("   ✅ WikiHow test completed successfully")
    except Exception as e:
        test_results['wikihow'] = False
        print(f"   ❌ WikiHow test failed: {e}")
    
    # Test 3: iFixit Connectivity
    print("\n3️⃣ Testing iFixit Connectivity...")
    try:
        from ifixit_tool import test_ifixit_connectivity
        test_ifixit_connectivity()
        test_results['ifixit'] = True
        print("   ✅ iFixit test completed successfully")
    except Exception as e:
        test_results['ifixit'] = False
        print(f"   ❌ iFixit test failed: {e}")
    
    # Test 4: iFixit API (Advanced)
    print("\n4️⃣ Testing iFixit API (Advanced)...")
    try:
        from ifixit_tool import test_ifixit_api_connectivity
        test_ifixit_api_connectivity()
        test_results['ifixit_api'] = True
        print("   ✅ iFixit API test completed successfully")
    except Exception as e:
        test_results['ifixit_api'] = False
        print(f"   ❌ iFixit API test failed: {e}")
    
    # Test 5: Manualslib Connectivity
    print("\n5️⃣ Testing Manualslib Connectivity...")
    try:
        from manualslib_tool import test_manualslib_connectivity
        test_manualslib_connectivity()
        test_results['manualslib'] = True
        print("   ✅ Manualslib test completed successfully")
    except Exception as e:
        test_results['manualslib'] = False
        print(f"   ❌ Manualslib test failed: {e}")
    
    # Test 6: Repair Manuals Search
    print("\n6️⃣ Testing Repair Manuals Search...")
    try:
        from test_repair_manuals import test_repair_manuals_connectivity
        test_repair_manuals_connectivity()
        test_results['repair_manuals'] = True
        print("   ✅ Repair manuals test completed successfully")
    except Exception as e:
        test_results['repair_manuals'] = False
        print(f"   ❌ Repair manuals test failed: {e}")
    
    # Test 7: Mock Agents
    print("\n7️⃣ Testing Mock Agents...")
    try:
        from test_mock_agents import test_all_mock_agents
        test_all_mock_agents()
        test_results['mock_agents'] = True
        print("   ✅ Mock agents test completed successfully")
    except Exception as e:
        test_results['mock_agents'] = False
        print(f"   ❌ Mock agents test failed: {e}")
    
    # Summary Report
    print("\n" + "=" * 60)
    print("📊 CONNECTIVITY TEST SUMMARY REPORT")
    print("=" * 60)
    
    successful_tests = sum(test_results.values())
    total_tests = len(test_results)
    
    print(f"✅ Successful tests: {successful_tests}/{total_tests}")
    print(f"📊 Success rate: {(successful_tests/total_tests)*100:.1f}%")
    
    print("\n📋 Detailed Results:")
    for test_name, success in test_results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {test_name:15} : {status}")
    
    print("\n🎯 Recommendations:")
    if test_results['llm']:
        print("   • LLM connectivity is working - you can run the full system")
    else:
        print("   • ❌ LLM connectivity failed - check Ollama setup")
    
    if test_results['wikihow']:
        print("   • WikiHow API is working - real search results available")
    else:
        print("   • ⚠️  WikiHow API failed - will use fallback")
    
    if test_results['ifixit']:
        print("   • iFixit API is working - real repair guides available")
    else:
        print("   • ⚠️  iFixit API failed - will use fallback")
    
    if test_results['manualslib']:
        print("   • Manualslib is working - real manual search available")
    else:
        print("   • ⚠️  Manualslib failed - will use fallback")
    
    if test_results['mock_agents']:
        print("   • Mock agents are ready - fallback functionality available")
    
    print("\n" + "=" * 60)
    if successful_tests == total_tests:
        print("🎉 ALL TESTS PASSED! Your system is ready to run.")
    elif successful_tests >= 3:
        print("⚠️  MOST TESTS PASSED! System can run with some limitations.")
    else:
        print("❌ MANY TESTS FAILED! Please check your setup before proceeding.")
    
    print("=" * 60)

def run_specific_test(test_name):
    """Run a specific test by name"""
    test_name = test_name.lower()
    
    if test_name == 'llm':
        from test_llm_connectivity import test_llm_connectivity
        test_llm_connectivity()
    elif test_name == 'wikihow':
        from wikihow_tool import test_wikihow_connectivity
        test_wikihow_connectivity()
    elif test_name == 'ifixit':
        from ifixit_tool import test_ifixit_connectivity
        test_ifixit_connectivity()
    elif test_name == 'ifixit_api':
        from ifixit_tool import test_ifixit_api_connectivity
        test_ifixit_api_connectivity()
    elif test_name == 'manualslib':
        from manualslib_tool import test_manualslib_connectivity
        test_manualslib_connectivity()
    elif test_name == 'repair_manuals':
        from test_repair_manuals import test_repair_manuals_connectivity
        test_repair_manuals_connectivity()
    elif test_name == 'mock':
        from test_mock_agents import test_all_mock_agents
        test_all_mock_agents()
    else:
        print(f"❌ Unknown test: {test_name}")
        print("Available tests: llm, wikihow, ifixit, ifixit_api, manualslib, repair_manuals, mock")
        print("Or run 'all' for comprehensive testing")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_arg = sys.argv[1].lower()
        if test_arg == 'all':
            run_connectivity_tests()
        else:
            run_specific_test(test_arg)
    else:
        print("🧪 Connectivity Test Runner")
        print("=" * 40)
        print("Usage:")
        print("  python run_all_tests.py all          # Run all tests")
        print("  python run_all_tests.py llm          # Test LLM only")
        print("  python run_all_tests.py wikihow      # Test WikiHow only")
        print("  python run_all_tests.py ifixit       # Test iFixit basic only")
        print("  python run_all_tests.py ifixit_api   # Test iFixit API advanced only")
        print("  python run_all_tests.py manualslib   # Test Manualslib only")
        print("  python run_all_tests.py repair_manuals # Test repair manuals search only")
        print("  python run_all_tests.py mock         # Test mock agents only")
        print("\nRunning all tests by default...")
        run_connectivity_tests()
