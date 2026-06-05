"""
GPU Device Manager for Drug Discovery Platform
Centralized device detection and management for all ML/DL operations
"""
import torch
import logging
from typing import Optional, Literal

logger = logging.getLogger(__name__)

class DeviceManager:
    """Manages device allocation and provides GPU utilities"""
    
    _device: Optional[torch.device] = None
    _device_name: str = "CPU"
    _vram_gb: float = 0.0
    
    @classmethod
    def get_device(cls) -> torch.device:
        """
        Get the optimal compute device (CUDA GPU or CPU fallback)
        
        Returns:
            torch.device: CUDA device if available, else CPU
        """
        if cls._device is None:
            cls._initialize_device()
        return cls._device
    
    @classmethod
    def _initialize_device(cls):
        """Initialize and detect available compute device"""
        try:
            if torch.cuda.is_available():
                cls._device = torch.device("cuda:0")
                cls._device_name = torch.cuda.get_device_name(0)
                cls._vram_gb = round(
                    torch.cuda.get_device_properties(0).total_memory / 1024**3, 
                    1
                )
                logger.info(
                    f"✅ GPU Initialized: {cls._device_name} "
                    f"({cls._vram_gb} GB VRAM)"
                )
            else:
                cls._device = torch.device("cpu")
                logger.warning("⚠️ GPU not available. Using CPU (slower performance)")
        except Exception as e:
            cls._device = torch.device("cpu")
            logger.error(f"Error detecting GPU: {e}. Falling back to CPU")
    
    @classmethod
    def get_device_info(cls) -> dict:
        """
        Get detailed device information
        
        Returns:
            dict: Device stats including name, type, VRAM, etc.
        """
        if cls._device is None:
            cls._initialize_device()
        
        info = {
            "device_type": cls._device.type,
            "device_name": cls._device_name,
            "is_cuda": cls._device.type == "cuda",
            "vram_gb": cls._vram_gb,
        }
        
        if torch.cuda.is_available():
            info.update({
                "cuda_version": torch.version.cuda,
                "pytorch_version": torch.__version__,
                "num_gpus": torch.cuda.device_count(),
                "current_vram_used": round(
                    torch.cuda.memory_allocated(0) / 1024**3, 2
                ),
                "current_vram_cached": round(
                    torch.cuda.memory_reserved(0) / 1024**3, 2
                ),
            })
        
        return info
    
    @classmethod
    def clear_cache(cls):
        """Clear GPU cache to free memory"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("🗑️ GPU cache cleared")
    
    @classmethod
    def get_optimal_batch_size(cls, model_size: Literal["small", "medium", "large"]) -> int:
        """
        Recommend batch size based on available VRAM
        
        Args:
            model_size: Size category of the model
            
        Returns:
            int: Recommended batch size
        """
        if not torch.cuda.is_available():
            return 1  # CPU fallback
        
        vram = cls._vram_gb
        
        if model_size == "small":  # <100M parameters
            if vram >= 8:
                return 32
            elif vram >= 6:
                return 16
            elif vram >= 4:
                return 8
            else:
                return 4
                
        elif model_size == "medium":  # 100M-1B parameters
            if vram >= 8:
                return 8
            elif vram >= 6:
                return 4
            elif vram >= 4:
                return 2
            else:
                return 1
                
        else:  # large (>1B parameters)
            if vram >= 12:
                return 4
            elif vram >= 8:
                return 2
            else:
                return 1
    
    @classmethod
    def move_to_device(cls, tensor_or_model):
        """
        Move tensor or model to the optimal device
        
        Args:
            tensor_or_model: PyTorch tensor or nn.Module
            
        Returns:
            Tensor or model on the target device
        """
        if cls._device is None:
            cls._initialize_device()
        return tensor_or_model.to(cls._device)
    
    @classmethod
    def print_status(cls):
        """Print detailed device status (useful for debugging)"""
        info = cls.get_device_info()
        
        print("\n" + "="*60)
        print("🔧 Device Status")
        print("="*60)
        print(f"Device Type:     {info['device_type'].upper()}")
        print(f"Device Name:     {info['device_name']}")
        
        if info['is_cuda']:
            print(f"CUDA Version:    {info['cuda_version']}")
            print(f"PyTorch Version: {info['pytorch_version']}")
            print(f"Total VRAM:      {info['vram_gb']} GB")
            print(f"VRAM Used:       {info['current_vram_used']} GB")
            print(f"VRAM Cached:     {info['current_vram_cached']} GB")
            print(f"GPUs Available:  {info['num_gpus']}")
        else:
            print("⚠️  GPU acceleration not available")
        print("="*60 + "\n")


# Global device instance (import this in your ML modules)
DEVICE = DeviceManager.get_device()


# Convenience functions
def get_device() -> torch.device:
    """Get the current compute device"""
    return DeviceManager.get_device()


def to_device(tensor_or_model):
    """Move tensor/model to device"""
    return DeviceManager.move_to_device(tensor_or_model)


def clear_gpu_cache():
    """Clear GPU memory cache"""
    DeviceManager.clear_cache()


def device_info() -> dict:
    """Get device information"""
    return DeviceManager.get_device_info()


def print_device_status():
    """Print device status"""
    DeviceManager.print_status()


if __name__ == "__main__":
    # Test device detection
    print_device_status()
    
    # Test device info
    info = device_info()
    print("\nDevice Info Dict:")
    for key, value in info.items():
        print(f"  {key}: {value}")
