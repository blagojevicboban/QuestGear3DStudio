
import os
import sys
import ssl
import certifi

print("[Launcher] Applying SSL fixes for Windows...")

# --- SSL MONKEY PATCH START ---
# Fix for ssl.SSLError: [ASN1] nested asn1 error (_ssl.c:4047)
# This error occurs when Python tries to load certificates from a corrupted Windows Certificate Store.
# We override the context creation to ONLY use the 'certifi' certificate bundle and IGNORE the Windows store.

def patched_create_default_context(purpose=ssl.Purpose.SERVER_AUTH, *, cafile=None, capath=None, cadata=None):
    """
    Custom SSL context creator that avoids loading Windows Store certificates.
    Instead, it strictly uses the certifi CA bundle.
    """
    # Create a raw TLS client context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    
    # Secure default options
    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3
    context.options |= ssl.OP_NO_COMPRESSION
    
    # Load the reliable certifi bundle
    try:
        context.load_verify_locations(cafile=certifi.where())
        # print(f"[Launcher] Loaded certificates from: {certifi.where()}")
    except Exception as e:
        print(f"[Launcher] WARNING: Failed to load certifi bundle: {e}")
    
    # Set verification mode
    if purpose == ssl.Purpose.SERVER_AUTH:
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = True
    
    return context

# Apply the patch to both the public and internal function used by urllib/http.client
ssl.create_default_context = patched_create_default_context
ssl._create_default_https_context = patched_create_default_context
# --- SSL MONKEY PATCH END ---

# Ensure critical dependencies are in path (fixes ModuleNotFoundError for some setups)
sys.path.append(os.getcwd())

def find_and_inject_msvc():
    """
    Attempts to find cl.exe (MSVC compiler) and add it to PATH.
    Crucial for 'gsplat' on Windows when Build Tools are installed but not in PATH.
    """
    import subprocess
    import shutil
    
    # If cl.exe is already in path, we are good
    if shutil.which("cl"):
        return True
        
    print("[Launcher] cl.exe (MSVC) not found in PATH. Attempting auto-discovery...")
    
    # Common locations for VS 2022 and 2026 (including BuildTools)
    possible_roots = []
    
    # Try to read from config.yml first
    try:
        import yaml
        config_path = os.path.join(os.getcwd(), 'config.yml')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                custom_path = config.get('app_settings', {}).get('msvc_path')
                if custom_path and os.path.exists(custom_path):
                    possible_roots.append(custom_path)
                    print(f"[Launcher] Using custom MSVC path from config: {custom_path}")
    except Exception as e:
        print(f"[Launcher] Note: Could not read config.yml for custom MSVC path: {e}")

    possible_roots.extend([
        r"C:\Program Files\Microsoft Visual Studio\2026\BuildTools",
        r"C:\Program Files\Microsoft Visual Studio\2026\Community",
        r"C:\Program Files\Microsoft Visual Studio\2022\BuildTools",
        r"C:\Program Files\Microsoft Visual Studio\2022\Community",
        r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools",
        r"C:\Program Files (x86)\Microsoft Visual Studio\2022\Community",
    ])
    
    # Common roots for Visual Studio installations
    vs_base = r"C:\Program Files\Microsoft Visual Studio"
    vs_base_x86 = r"C:\Program Files (x86)\Microsoft Visual Studio"
    
    search_roots = []
    if os.path.exists(vs_base):
        try:
            # Add all subdirectories (years/versions like 2022, 2026, 18)
            for d in os.listdir(vs_base):
                version_path = os.path.join(vs_base, d)
                if os.path.isdir(version_path):
                    # Add both BuildTools and Community/Professional/Enterprise
                    for flavor in ["BuildTools", "Community", "Professional", "Enterprise"]:
                        search_roots.append(os.path.join(version_path, flavor))
        except: pass

    if os.path.exists(vs_base_x86):
        try:
            for d in os.listdir(vs_base_x86):
                version_path = os.path.join(vs_base_x86, d)
                if os.path.isdir(version_path):
                    for flavor in ["BuildTools", "Community", "Professional", "Enterprise"]:
                        search_roots.append(os.path.join(version_path, flavor))
        except: pass

    possible_roots.extend(search_roots)
    
    # Remove duplicates but keep order
    seen = set()
    possible_roots = [x for x in possible_roots if not (x in seen or seen.add(x))]
    
    found_any = False
    for root in possible_roots:
        # Check standard MSVC path
        msvc_base = os.path.join(root, "VC", "Tools", "MSVC")
        if not os.path.exists(msvc_base):
            # Sometimes it's slightly different, try to find "Tools/MSVC" recursively in VC
            vc_base = os.path.join(root, "VC")
            if not os.path.exists(vc_base):
                continue
            
            # Simple recursive search for MSVC folder if root/VC/Tools/MSVC fails
            msvc_found = False
            for r, dirs, files in os.walk(vc_base):
                if "MSVC" in dirs and "Tools" in r:
                    msvc_base = os.path.join(r, "MSVC")
                    msvc_found = True
                    break
            if not msvc_found: continue
            
        # Find the latest version folder
        try:
            versions = sorted(os.listdir(msvc_base), reverse=True)
            if not versions: continue
            
            # Try Hostx64/x64 first (preferred for modern machines)
            bin_path = os.path.join(msvc_base, versions[0], "bin", "Hostx64", "x64")
            if not os.path.exists(os.path.join(bin_path, "cl.exe")):
                # Fallback to Hostx86/x86 if needed
                bin_path = os.path.join(msvc_base, versions[0], "bin", "Hostx86", "x86")
            
            if os.path.exists(os.path.join(bin_path, "cl.exe")):
                print(f"[Launcher] Found MSVC compiler at: {bin_path}")
                os.environ["PATH"] = bin_path + os.pathsep + os.environ["PATH"]
                found_any = True
                break
        except Exception:
            continue
            
    if not found_any:
        print("[Launcher] Auto-discovery failed. Compilation might fail.")
    return found_any

if __name__ == "__main__":
    # Inject MSVC if needed before importing nerfstudio (which might trigger checks)
    find_and_inject_msvc()
    
    try:
        print(f"[Launcher] Starting NerfStudio training with arguments: {sys.argv[1:]}")
        from nerfstudio.scripts.train import entrypoint
        sys.exit(entrypoint())
    except ImportError as e:
        print(f"[Launcher] CRITICAL ERROR: Could not import NerfStudio: {e}")
        print("Please ensure nerfstudio is installed: pip install nerfstudio")
        sys.exit(1)
    except (Exception, SystemExit) as e:
        error_msg = str(e)
        # Handle cases where e is just an exit code integer (like from SystemExit)
        if error_msg == "1" or not error_msg:
            error_msg = "NerfStudio encountered an internal error"
            
        print(f"[Launcher] ERROR: {error_msg}")
        
        # Specific check for gsplat compilation issues on Windows
        msg_lower = error_msg.lower()
        if "gsplat" in msg_lower or "cl.exe" in msg_lower or "where', 'cl" in msg_lower or "csrc" in msg_lower:
            print("\n" + "="*60)
            print("💎 GAUSSIAN SPLATTING (gsplat) ERROR DETECTED")
            print("="*60)
            print("The 'splatfacto' method requires C++ compilation but your system is missing")
            print("the Visual Studio C++ Compiler (cl.exe).")
            print("\nTO FIX THIS:")
            print("1. Install 'Visual Studio Build Tools' with 'C++ Desktop Development'.")
            print("2. OR: Switch 'Training Method' to 'nerfacto' in Settings.")
            print("   (Nerfacto is slower but doesn't require a C++ compiler).")
            print("="*60 + "\n")
        elif not isinstance(e, SystemExit):
            import traceback
            traceback.print_exc()
        sys.exit(1)
