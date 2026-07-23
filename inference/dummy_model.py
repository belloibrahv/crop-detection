"""
Script to generate a dummy SavedModel for testing.
This is just a placeholder - you should train a real model using PlantVillage dataset.
"""
import tensorflow as tf
import os

# Create a simple dummy model
model = tf.keras.Sequential([
    tf.keras.layers.Input(shape=(224, 224, 3)),
    tf.keras.layers.GlobalAveragePooling2D(),
    tf.keras.layers.Dense(29, activation='softmax')  # 29 classes matching class_indices.json
])

model.compile(optimizer='adam', loss='categorical_crossentropy')

# Save the model
model_path = os.path.join(os.path.dirname(__file__), 'models', 'v1')
os.makedirs(model_path, exist_ok=True)
model.save(model_path)
print(f"Dummy model saved to {model_path}")
