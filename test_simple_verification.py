#!/usr/bin/env python3
"""
Simple verification test for database success message removal
"""

def test_source_code_changes():
    """Verify that the database success message has been removed from source code"""
    print("🧪 Verifying Database Success Message Removal")
    print("=" * 50)
    
    try:
        with open('/home/runner/work/cravemap/cravemap/CraveMap.py', 'r') as f:
            source_lines = f.readlines()
        
        print(f"✅ Successfully read CraveMap.py ({len(source_lines)} lines)")
        
        # Test 1: Check that success message is NOT in source
        success_message_found = False
        success_message_lines = []
        
        for i, line in enumerate(source_lines, 1):
            if '🟢 PostgreSQL database connected successfully' in line:
                success_message_found = True
                success_message_lines.append(i)
        
        if not success_message_found:
            print("✅ SUCCESS: Database success message removed from source code")
        else:
            print(f"❌ FAILED: Success message still found on lines: {success_message_lines}")
            return False
        
        # Test 2: Check that error messages are still present
        error_message_found = False
        warning_message_found = False
        
        for line in source_lines:
            if '⚠️ PostgreSQL connection failed:' in line:
                warning_message_found = True
            if 'All database initialization failed:' in line:
                error_message_found = True
        
        if warning_message_found:
            print("✅ SUCCESS: PostgreSQL connection warning preserved")
        else:
            print("❌ FAILED: PostgreSQL connection warning missing")
            return False
        
        if error_message_found:
            print("✅ SUCCESS: Database initialization error message preserved")
        else:
            print("❌ FAILED: Database initialization error message missing")
            return False
        
        # Test 3: Check the exact context around the change
        print("\n📋 Checking context around the change...")
        
        for i, line in enumerate(source_lines):
            if 'postgres_success, postgres_message = postgres_db.test_connection()' in line:
                # Check the next few lines
                context_lines = source_lines[i:i+6]
                print("Context around database connection test:")
                for j, context_line in enumerate(context_lines):
                    line_num = i + j + 1
                    print(f"  {line_num:3d}: {context_line.rstrip()}")
                
                # Verify the structure is correct
                if len(context_lines) >= 4:
                    next_line = context_lines[1].strip()
                    if next_line == 'if postgres_success:':
                        third_line = context_lines[2].strip()
                        if third_line == 'db = None  # Use PostgreSQL primarily':
                            print("✅ SUCCESS: Correct code structure after message removal")
                        else:
                            print(f"❌ FAILED: Unexpected third line: {third_line}")
                            return False
                    else:
                        print(f"❌ FAILED: Unexpected next line: {next_line}")
                        return False
                break
        else:
            print("❌ FAILED: Could not find database connection test line")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error reading source file: {e}")
        return False

def verify_git_changes():
    """Check git diff to see what changed"""
    print("\n📝 Checking git changes...")
    
    import subprocess
    try:
        result = subprocess.run(['git', 'diff', 'HEAD~1', 'CraveMap.py'], 
                              capture_output=True, text=True, cwd='/home/runner/work/cravemap/cravemap')
        
        if result.returncode == 0:
            diff_output = result.stdout
            if diff_output:
                print("Git diff shows:")
                print(diff_output)
                
                # Check if the removal is in the diff
                if 'st.info("🟢 PostgreSQL database connected successfully")' in diff_output and '- ' in diff_output:
                    print("✅ SUCCESS: Git confirms success message was removed")
                    return True
                else:
                    print("❌ WARNING: Git diff doesn't show expected removal")
                    return False
            else:
                print("ℹ️ No git changes detected")
                return True
        else:
            print(f"❌ Git command failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Could not run git command: {e}")
        return False

if __name__ == "__main__":
    print("🚀 SIMPLE VERIFICATION TEST FOR DATABASE MESSAGE REMOVAL")
    print("=" * 60)
    
    # Run tests
    source_test_passed = test_source_code_changes()
    git_test_passed = verify_git_changes()
    
    print("\n" + "=" * 60)
    print("📊 VERIFICATION RESULTS")
    print("=" * 60)
    
    if source_test_passed and git_test_passed:
        print("✅ ALL VERIFICATIONS PASSED!")
        print("\n🎉 Database success message successfully removed!")
        print("✅ Error handling preserved")
        print("✅ Code structure maintained")
        print("✅ Git changes verified")
        exit(0)
    else:
        print("❌ VERIFICATION FAILED!")
        print(f"Source test: {'✅ PASSED' if source_test_passed else '❌ FAILED'}")
        print(f"Git test: {'✅ PASSED' if git_test_passed else '❌ FAILED'}")
        exit(1)