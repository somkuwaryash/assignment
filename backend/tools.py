"""
Data analysis tools for the LangGraph agent
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import traceback
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from io import BytesIO
import warnings

# Suppress matplotlib warnings
warnings.filterwarnings('ignore', category=UserWarning)

class DataAnalysisTools:
    """Tools for analyzing the NYC 311 dataset"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.dataset_info = self._generate_dataset_info()
    
    def _generate_dataset_info(self) -> str:
        """Generate comprehensive dataset information for AI context"""
        info_parts = []
        
        # Basic info
        info_parts.append(f"Dataset Shape: {self.df.shape[0]:,} rows × {self.df.shape[1]} columns")
        info_parts.append(f"\nColumn Names and Types:")
        
        for col in self.df.columns[:30]:  # First 30 columns
            dtype = str(self.df[col].dtype)
            non_null = self.df[col].count()
            null_pct = (1 - non_null/len(self.df)) * 100
            info_parts.append(f"  - {col}: {dtype} ({null_pct:.1f}% null)")
        
        # Sample data
        info_parts.append(f"\nFirst 5 rows sample:")
        info_parts.append(self.df.head(5).to_string())
        
        # Key statistics for important columns
        if 'Complaint Type' in self.df.columns:
            top_complaints = self.df['Complaint Type'].value_counts().head(10)
            info_parts.append(f"\nTop 10 Complaint Types:")
            info_parts.append(top_complaints.to_string())
        
        if 'Borough' in self.df.columns:
            borough_counts = self.df['Borough'].value_counts()
            info_parts.append(f"\nComplaints by Borough:")
            info_parts.append(borough_counts.to_string())
        
        return "\n".join(info_parts)
    
    def get_dataset_context(self) -> str:
        """Return dataset context for AI"""
        return self.dataset_info
    
    def execute_pandas_code(self, code: str) -> Dict[str, Any]:
        """
        Safely execute pandas code and return results
        
        Args:
            code: Python/pandas code to execute
            
        Returns:
            Dict with 'success', 'result', 'error', and 'result_type'
        """
        try:
            # Create safe execution namespace
            namespace = {
                'pd': pd,
                'np': np,
                'df': self.df.copy(),  # Work on copy to prevent modifications
                'result': None
            }
            
            # Execute code
            exec(code, namespace)
            result = namespace.get('result')
            
            if result is None:
                return {
                    'success': False,
                    'result': None,
                    'error': 'Code executed but no result was stored in "result" variable',
                    'result_type': None
                }
            
            # Determine result type and format
            result_type = type(result).__name__
            
            if isinstance(result, pd.DataFrame):
                formatted_result = result.to_string(max_rows=50)
                result_data = result
            elif isinstance(result, pd.Series):
                formatted_result = result.to_string(max_rows=50)
                result_data = result
            elif isinstance(result, (int, float)):
                formatted_result = f"{result:,.4f}".rstrip('0').rstrip('.')
                result_data = result
            elif isinstance(result, dict):
                formatted_result = str(result)
                result_data = result
            else:
                formatted_result = str(result)
                result_data = result
            
            return {
                'success': True,
                'result': formatted_result,
                'result_data': result_data,
                'error': None,
                'result_type': result_type
            }
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            return {
                'success': False,
                'result': None,
                'error': error_msg,
                'result_type': None
            }
    
    def execute_visualization_code(self, viz_code: str) -> Dict[str, Any]:
        """
        Execute matplotlib/seaborn visualization code and return base64 image or error
        
        Args:
            viz_code: Python code that creates a matplotlib/seaborn visualization
            
        Returns:
            Dict with 'success', 'image' (base64), and 'error'
        """
        try:
            # Create safe execution namespace with visualization libraries
            namespace = {
                'pd': pd,
                'np': np,
                'df': self.df.copy(),
                'plt': plt,
                'sns': sns,
                'fig': None,
                'ax': None
            }
            
            # Execute visualization code
            exec(viz_code, namespace)
            
            # Convert to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close('all')
            
            return {
                'success': True,
                'image': image_base64,
                'error': None
            }
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            print(f"Visualization execution error: {e}")
            traceback.print_exc()
            plt.close('all')
            
            return {
                'success': False,
                'image': None,
                'error': error_msg
            }