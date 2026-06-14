from PIL import Image
import numpy as np
import torch
from torch import nn
from torchvision import transforms
from torchvision.models import resnet34, ResNet34_Weights


def get_ready_model(num_classes=3):
    weights = ResNet34_Weights.DEFAULT
    model = resnet34(weights=weights)
    
    for param in model.parameters():
        param.requires_grad = False
        
    in_features = model.fc.in_features
    
    model.fc = nn.Sequential(
        nn.Linear(in_features, 256),
        nn.BatchNorm1d(256),
        nn.ReLU(),
        nn.Dropout(0.2),
        nn.Linear(256, num_classes) 
    )
    
    return model

class ModelUser:
    def __init__(self, model, device, class_names=['bad', 'regular', 'good']):
        self.model = model
        self.model.eval()
        self.device = device
        
        self.transform = transforms.Compose([
            # transforms.Resize(416),
            # transforms.Lambda(lambda img: img.crop((
            #     img.width // 2 - 208,
            #     (img.height // 2) * (img.height // 2 > 416) + img.height - 416 * (img.height // 2 <= 416),
            #     img.width // 2 + 208,
            #     (img.height // 2) * (img.height // 2 > 416) + img.height - 416 * (img.height // 2 <= 416) + 416
            # ))),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        self.class_names = class_names

    def predict_image(self, image_path):
        image = Image.open(image_path).convert('RGB')
        input_tensor = self.transform(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            output = self.model(input_tensor)
            probabilities = torch.softmax(output, dim=1)[0]
            target_index = probabilities.argmax().item()
        
        return self.class_names[target_index]
