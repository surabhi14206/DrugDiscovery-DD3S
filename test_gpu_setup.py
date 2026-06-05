"""
GPU Setup Verification Script
Run this after installing PyTorch with CUDA to verify GPU acceleration
"""
import sys
import subprocess

def check_nvidia_driver():
    """Check NVIDIA driver installation"""
    print("\n" + "="*70)
    print("1️⃣  NVIDIA Driver Check")
    print("="*70)
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ NVIDIA driver installed")
            # Parse output for key info
            lines = result.stdout.split('\n')
            for line in lines:
                if 'Driver Version' in line:
                    print(f"   {line.strip()}")
                if 'CUDA Version' in line:
                    idx = line.find('CUDA Version')
                    print(f"   Max CUDA support: {line[idx:idx+25]}")
                if 'GeForce RTX' in line or 'NVIDIA' in line:
                    if '|' in line:
                        parts = line.split('|')
                        for part in parts:
                            if 'GeForce' in part or 'RTX' in part:
                                print(f"   GPU: {part.strip()}")
                                break
            return True
        else:
            print("❌ nvidia-smi failed")
            return False
    except FileNotFoundError:
        print("❌ nvidia-smi not found - NVIDIA driver not installed")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_pytorch():
    """Check PyTorch installation and GPU support"""
    print("\n" + "="*70)
    print("2️⃣  PyTorch Installation Check")
    print("="*70)
    try:
        import torch
        print(f"✅ PyTorch installed: {torch.__version__}")
        
        # Check CUDA support
        print("\n" + "="*70)
        print("3️⃣  CUDA Support Check")
        print("="*70)
        
        cuda_available = torch.cuda.is_available()
        print(f"CUDA available: {'✅ YES' if cuda_available else '❌ NO (CPU-only)'}")
        
        if cuda_available:
            print(f"CUDA version (PyTorch): {torch.version.cuda}")
            print(f"cuDNN version: {torch.backends.cudnn.version()}")
            print(f"Number of GPUs: {torch.cuda.device_count()}")
            
            # GPU details
            print("\n" + "="*70)
            print("4️⃣  GPU Details")
            print("="*70)
            for i in range(torch.cuda.device_count()):
                gpu_name = torch.cuda.get_device_name(i)
                gpu_props = torch.cuda.get_device_properties(i)
                vram_gb = round(gpu_props.total_memory / 1024**3, 2)
                compute_cap = f"{gpu_props.major}.{gpu_props.minor}"
                
                print(f"\nGPU {i}:")
                print(f"  Name: {gpu_name}")
                print(f"  VRAM: {vram_gb} GB")
                print(f"  Compute Capability: {compute_cap}")
                print(f"  Multi-Processor Count: {gpu_props.multi_processor_count}")
            
            # Memory test
            print("\n" + "="*70)
            print("5️⃣  Memory Allocation Test")
            print("="*70)
            try:
                test_tensor = torch.rand(1000, 1000, device='cuda')
                print(f"✅ GPU tensor created: shape {test_tensor.shape}")
                print(f"   Memory allocated: {round(torch.cuda.memory_allocated(0) / 1024**2, 2)} MB")
                print(f"   Memory cached: {round(torch.cuda.memory_reserved(0) / 1024**2, 2)} MB")
                del test_tensor
                torch.cuda.empty_cache()
                print("✅ Memory cleanup successful")
                
                return True
            except Exception as e:
                print(f"❌ GPU memory test failed: {e}")
                return False
        else:
            print("\n⚠️  GPU NOT DETECTED")
            print("\nPossible reasons:")
            print("  1. PyTorch installed without CUDA support (CPU-only)")
            print("  2. Incorrect CUDA version for your GPU driver")
            print("  3. NVIDIA driver not installed or outdated")
            print("\nSolution:")
            print("  Uninstall current PyTorch and reinstall with CUDA:")
            print("  pip uninstall torch torchvision torchaudio")
            print("  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126")
            return False
            
    except ImportError:
        print("❌ PyTorch not installed")
        print("\nInstall with:")
        print("  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_device_manager():
    """Check custom DeviceManager"""
    print("\n" + "="*70)
    print("6️⃣  DeviceManager Integration Check")
    print("="*70)
    try:
        from apps.neural_networks.device_manager import DeviceManager
        
        DeviceManager.print_status()
        
        info = DeviceManager.get_device_info()
        if info['is_cuda']:
            print("✅ DeviceManager correctly detects GPU")
            
            # Test optimal batch size
            print("\n📊 Recommended Batch Sizes (for your VRAM):")
            for model_size in ['small', 'medium', 'large']:
                batch = DeviceManager.get_optimal_batch_size(model_size)
                print(f"  {model_size.capitalize()} models: {batch}")
            
            return True
        else:
            print("⚠️  DeviceManager fallback to CPU")
            return False
            
    except ImportError as e:
        print(f"⚠️  DeviceManager not found: {e}")
        print("   (Optional - project-specific utility)")
        return True  # Don't fail on this
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_simple_model():
    """Test a simple neural network on GPU"""
    print("\n" + "="*70)
    print("7️⃣  Simple Model Training Test")
    print("="*70)
    try:
        import torch
        import torch.nn as nn
        
        if not torch.cuda.is_available():
            print("⏭️  Skipping (GPU not available)")
            return True
        
        device = torch.device('cuda')
        
        # Simple linear model
        model = nn.Linear(10, 1).to(device)
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        
        # Dummy data
        x = torch.randn(32, 10, device=device)
        y = torch.randn(32, 1, device=device)
        
        # Training step
        import time
        start = time.time()
        
        for _ in range(100):
            optimizer.zero_grad()
            output = model(x)
            loss = criterion(output, y)
            loss.backward()
            optimizer.step()
        
        elapsed = time.time() - start
        
        print(f"✅ Trained 100 iterations in {elapsed:.3f} seconds")
        print(f"   Final loss: {loss.item():.6f}")
        print(f"   GPU utilized successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return False

def main():
    """Run all checks"""
    print("\n" + "🚀" * 35)
    print("   GPU SETUP VERIFICATION FOR DRUG DISCOVERY PLATFORM")
    print("🚀" * 35)
    
    results = []
    
    results.append(("NVIDIA Driver", check_nvidia_driver()))
    results.append(("PyTorch & CUDA", check_pytorch()))
    results.append(("DeviceManager", check_device_manager()))
    results.append(("Model Training", test_simple_model()))
    
    # Summary
    print("\n" + "="*70)
    print("📋 VERIFICATION SUMMARY")
    print("="*70)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:12} {name}")
        if not passed and name != "DeviceManager":  # DeviceManager is optional
            all_passed = False
    
    print("="*70)
    
    if all_passed:
        print("\n🎉 SUCCESS! GPU acceleration is ready!")
        print("\nNext steps:")
        print("  1. Run your Django server: python manage.py runserver")
        print("  2. Try ML-based molecule generation (will use GPU)")
        print("  3. Monitor GPU usage with: watch -n 1 nvidia-smi")
    else:
        print("\n⚠️  Some checks failed. Review errors above.")
        print("\nCommon fixes:")
        print("  • Update NVIDIA driver from nvidia.com")
        print("  • Reinstall PyTorch with correct CUDA version")
        print("  • Check GPU is not disabled in laptop power settings")
    
    print("\n")

if __name__ == "__main__":
    main()
