"""
Model Manager and Factory for EpiSense NLP Pipeline.
Provides cached singletons of en_core_web_sm and en_core_sci_sm with
runtime configuration handling.
"""

from typing import Optional
import spacy
from spacy.language import Language

from episense.exceptions import ConfigurationError


class ModelManager:
    """
    Manages local spaCy and scispaCy model instances with safe runtime configurations.
    """

    _web_nlp: Optional[Language] = None
    _sci_nlp: Optional[Language] = None

    @classmethod
    def get_web_model(cls, model_name: str = "en_core_web_sm") -> Language:
        """
        Loads and returns the general English spaCy model.
        """
        if cls._web_nlp is None:
            try:
                cls._web_nlp = spacy.load(model_name)
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to load required spaCy general model '{model_name}'. "
                    f"Ensure it is installed via 'python -m spacy download {model_name}'. Details: {e}"
                )
        return cls._web_nlp

    @classmethod
    def get_sci_model(cls, model_name: str = "en_core_sci_sm") -> Language:
        """
        Loads and returns the scispaCy biomedical model with runtime config override.
        """
        if cls._sci_nlp is None:
            try:
                # Runtime override to ensure compatibility with confection v2 / strict pydantic bool
                cls._sci_nlp = spacy.load(
                    model_name,
                    config={
                        "components": {
                            "tok2vec": {
                                "model": {
                                    "embed": {
                                        "include_static_vectors": False
                                    }
                                }
                            }
                        }
                    },
                )
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to load required scispaCy biomedical model '{model_name}'. "
                    f"Details: {e}"
                )
        return cls._sci_nlp
