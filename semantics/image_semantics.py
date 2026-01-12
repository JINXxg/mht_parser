
from typing import Optional
from model.mht_model import OcrResult

import shutil 
# semantics/image_semantics.py
class OcrInterpreter:
    def __init__(self, engine: str = "tesseract", lang: str = "chi_sim+eng"):
        self.engine = engine
        self.lang = lang
        self._log_limit = 5
        self._logged = 0

    def _check_tesseract(self) -> Optional[str]:
        if shutil.which("tesseract") is None:
            return "tesseract not found in PATH. Install it (e.g., brew install tesseract) or set PATH."
        return None
    

    def interpret(self, image_path: str) -> str:
        # TODO: 接入 pytesseract / easyocr / 或调用你的视觉模型
        # 先返回占位，确保管道跑通
        return self.interpret_rich(image_path).text


    def interpret_rich(self, image_path: str) -> OcrResult:
        if self.engine != "tesseract":
            result = OcrResult(text="", method=self.engine, error=f"Unsupported engine: {self.engine}")
            self._log_result(image_path, result)
            return result

        err = self._check_tesseract()
        if err:
            result = OcrResult(text="", method="tesseract", error=err)
            self._log_result(image_path, result)
            return result

        try:
            from PIL import Image, ImageOps
            import pytesseract
        except Exception as e:
            result = OcrResult(text="", method="tesseract", error=f"Missing deps: {e}")
            self._log_result(image_path, result)
            return result

        try:
            img = Image.open(image_path)

            # 预处理：灰度 + 自适应对比（对截图、流程图文字通常更稳）
            img = ImageOps.grayscale(img)
            img = ImageOps.autocontrast(img)

            # 简单放大：小字/截图常见，放大可提升召回
            w, h = img.size
            if max(w, h) < 1600:
                img = img.resize((w * 2, h * 2))

            # OCR 配置：psm 6（假设一块文本区域）
            config = "--psm 6"
            text = pytesseract.image_to_string(img, lang=self.lang, config=config)
            text = (text or "").strip()

            result = OcrResult(text=text, method="tesseract", error=None)
        except Exception as e:
            result = OcrResult(text="", method="tesseract", error=str(e))

        self._log_result(image_path, result)
        return result

    def _log_result(self, image_path: str, result: OcrResult) -> None:
        if self._logged >= self._log_limit:
            return

        preview = (result.text or "").replace("\n", " ")
        if len(preview) > 60:
            preview = preview[:57] + "..."
        status = "error" if result.error else "ok"
        error_info = f" error={result.error}" if result.error else ""
        print(f"[OCR] {status} {image_path} ({result.method}){error_info}: {preview}")
        self._logged += 1