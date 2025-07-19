python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
    # For TensorFlow:
    # python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"