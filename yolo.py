from ultralytics import YOLO

class Yolo:
    def __init__(self, model_path: str):
        self.model = YOLO(model_path)

    def predict(self, image_path: str):
        results = self.model(image_path)
        return results
    
import onnxruntime as ort
class YoloONNX:
    def __init__(self, model_path: str):
        self.session = ort.InferenceSession(model_path)

    def predict(self, input_data):
        input_name = self.session.get_inputs()[0].name
        output_name = self.session.get_outputs()[0].name
        return self.session.run([output_name], {input_name: input_data})