from PIL import Image
import numpy as np

import torch
from torch import nn
from torchvision import transforms

class RoadClassifier(nn.Module):
    def __init__(self, inp, out, hidden_size, act='relu'):
        super().__init__()
        # Сначала уменьшаем картинку свертками
        self.feature_extractor = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=3, stride=2, padding=1, bias=False), # 416 -> 208
            nn.ReLU(),
            nn.BatchNorm2d(16),
            nn.MaxPool2d(2), # 208 -> 104
            nn.Conv2d(16, 32, kernel_size=3, stride=2, padding=1, bias=False), # 104 -> 52
            nn.ReLU(),
            nn.BatchNorm2d(32),
            nn.MaxPool2d(2), # 52 -> 26
            nn.Flatten()
        )

        inp = 32 * 26 * 26

        self.act = nn.ModuleDict({
            'relu': nn.ReLU()
        })
        self.layers = nn.ModuleList()
        for i in range(int(np.log2(hidden_size) - 1)):
            self.layers.add_module(f'linear_{i}', nn.Linear(inp, hidden_size))
            self.layers.add_module(f'act_{i}', self.act[act])
            inp = hidden_size
            hidden_size = int(hidden_size / 2)
        self.layers.add_module(f'layer_{i+1}', nn.Linear(inp, out))

    def forward(self, x):
        x = self.feature_extractor(x)

        for layer in self.layers:
            x = layer(x)
        return x

class ModelUser:
    def __init__(self, model_name):
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        param_model = torch.load(model_name, map_location=torch.device(device))
        self.model = RoadClassifier(inp=3 * 416**2, out=6, hidden_size=2048, act='relu').to(device=device)
        self.model.load_state_dict(param_model)
        self.model.eval()
        self.device = device

        # Оптимизируем трансформации
        self.transform = transforms.Compose([
            transforms.Resize(416),
            transforms.Lambda(lambda img: img.crop((0, img.height - 416, 416, img.height))),
            transforms.ToTensor()
        ])

        self.class_names = [
            '01_asphalt(Good)', '02_asphalt(Regular)', '03_asphalt(Bad)',
            '04_paved', '05_unpaved(Regular)', '06_unpaved(Bad)'
        ]

    def predict_image(self, image_path):
        image = Image.open(image_path).convert('RGB')
        input_tensor = self.transform(image).unsqueeze(0).to(self.device)

        with torch.set_grad_enabled(True):
            output = self.model(input_tensor)
            target_index = output.argmax(1).item()

        return self.class_names[target_index]