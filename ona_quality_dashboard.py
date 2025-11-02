import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ONAQualityDashboard:
    def __init__(self, data_file, config=None):
        """Initialize dashboard with data file and optional config"""
        self.data_file = data_file
        self.config = config or {}
        self.df = None
        self.district_col = None
        self.target_districts = ['Bosaso', 'Dhusamareb', 'Beletweyne', 'Baki', 'Gabiley']
        
    def load_data(self):
        """Load data from CSV file"""
        try:
            self.df = pd.read_csv(self.data_file)
            logger.info(f"Loaded {len(self.df)} records")
            
            # Convert dates
            if '_submission_time' in self.df.columns:
                self.df['_submission_time'] = pd.to_datetime(self.df['_submission_time'], errors='coerce')
                    
            return True
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return False
    
    def _find_column(self, column_name, keywords):
        """Find column by keywords"""
        if column_name and column_name in self.df.columns:
            return column_name
        
        for col in self.df.columns:
            if any(keyword.lower() in col.lower() for keyword in keywords):
                logger.info(f"Found column '{col}' for {keywords}")
                return col
        return None
    
    def generate_dashboard(self, output_file='ona_dashboard.html', 
                          title='ONA Data Quality Dashboard',
                          district_column='district',
                          duration_column='duration_minutes',
                          enumerator_column=None):
        """Generate MINIMAL FAST dashboard - 4 key visualizations only"""
        
        if self.df is None or len(self.df) == 0:
            logger.error("No data available")
            return False
        
        try:
            logger.info("🚀 Generating MINIMAL dashboard...")
            
            # Find columns
            district_column = self._find_column(district_column, ['district', 'District_id'])
            self.district_col = district_column
            enumerator_column = self._find_column(enumerator_column, ['enum', 'enumerator'])
            
            min_duration_threshold = 50
            
            # Mark validity
            if duration_column in self.df.columns:
                self.df['is_valid'] = self.df[duration_column] >= min_duration_threshold
            
            # Create figure with ONLY 3 rows
            fig = make_subplots(
                rows=3, cols=2,
                subplot_titles=(
                    '📊 Surveys by District',
                    '⏱️ Duration Distribution',
                    '⚠️ Validity Status',
                    '👥 Top Enumerators',
                    '📈 Daily Trends',
                    '📋 Key Stats'
                ),
                specs=[
                    [{"type": "bar"}, {"type": "box"}],
                    [{"type": "bar"}, {"type": "bar"}],
                    [{"type": "scatter"}, {"type": "table"}]
                ],
                row_heights=[0.33, 0.33, 0.34],
                vertical_spacing=0.12,
                horizontal_spacing=0.15
            )
            
            colors = {'primary': '#667eea', 'success': '#4caf50', 'danger': '#f44336'}
            
            # 1. SURVEYS BY DISTRICT
            logger.info("Adding districts...")
            if district_column and district_column in self.df.columns:
                district_data = self.df[district_column].value_counts().head(10)
                fig.add_trace(go.Bar(
                    x=district_data.index,
                    y=district_data.values,
                    marker_color=colors['primary'],
                    text=district_data.values,
                    textposition='outside',
                    showlegend=False
                ), row=1, col=1)
            
            # 2. DURATION BOX PLOT (sampled)
            logger.info("Adding duration...")
            if duration_column in self.df.columns:
                sample_data = self.df[duration_column].dropna().sample(n=min(500, len(self.df)))
                fig.add_trace(go.Box(
                    y=sample_data,
                    marker_color=colors['primary'],
                    showlegend=False
                ), row=1, col=2)
                fig.add_hline(y=min_duration_threshold, line_color="red", line_width=2, row=1, col=2)
            
            # 3. VALIDITY STATUS
            logger.info("Adding validity...")
            if 'is_valid' in self.df.columns:
                valid = self.df['is_valid'].sum()
                invalid = (~self.df['is_valid']).sum()
                fig.add_trace(go.Bar(
                    x=['✅ Valid (≥50min)', '❌ Invalid (<50min)'],
                    y=[valid, invalid],
                    marker=dict(color=[colors['success'], colors['danger']]),
                    text=[valid, invalid],
                    textposition='outside',
                    showlegend=False
                ), row=2, col=1)
            
            # 4. TOP ENUMERATORS
            logger.info("Adding enumerators...")
            if enumerator_column and enumerator_column in self.df.columns:
                enum_data = self.df[enumerator_column].value_counts().head(8)
                fig.add_trace(go.Bar(
                    x=enum_data.index,
                    y=enum_data.values,
                    marker_color='#4facfe',
                    text=enum_data.values,
                    textposition='outside',
                    showlegend=False
                ), row=2, col=2)
            
            # 5. DAILY TRENDS
            logger.info("Adding trends...")
            if '_submission_time' in self.df.columns:
                daily_data = self.df.groupby(self.df['_submission_time'].dt.date).size()
                fig.add_trace(go.Scatter(
                    x=daily_data.index,
                    y=daily_data.values,
                    mode='lines+markers',
                    line=dict(color=colors['primary'], width=2),
                    fill='tozeroy',
                    showlegend=False
                ), row=3, col=1)
            
            # 6. KEY STATS TABLE
            logger.info("Adding stats...")
            stats = {}
            stats['Total Surveys'] = f"{len(self.df):,}"
            
            if 'is_valid' in self.df.columns:
                valid_pct = (self.df['is_valid'].sum() / len(self.df) * 100)
                stats['Valid %'] = f"{valid_pct:.0f}%"
                stats['Invalid Count'] = f"{(~self.df['is_valid']).sum()}"
            
            if district_column and district_column in self.df.columns:
                stats['Districts'] = f"{self.df[district_column].nunique()}"
            
            if enumerator_column and enumerator_column in self.df.columns:
                stats['Enumerators'] = f"{self.df[enumerator_column].nunique()}"
            
            if duration_column and duration_column in self.df.columns:
                stats['Avg Duration'] = f"{self.df[duration_column].mean():.0f} min"
            
            fig.add_trace(go.Table(
                header=dict(
                    values=['<b>Metric</b>', '<b>Value</b>'],
                    fill_color=colors['primary'],
                    font=dict(color='white', size=12),
                    align='left'
                ),
                cells=dict(
                    values=[list(stats.keys()), list(stats.values())],
                    fill_color=[['#f0f4f8', '#ffffff'] * 10],
                    font=dict(size=11),
                    align='left'
                )
            ), row=3, col=2)
            
            # Update layout - MINIMAL
            logger.info("Finalizing...")
            fig.update_layout(
                height=1200,
                showlegend=False,
                title={
                    'text': f'<b>{title}</b><br><sup>Updated: {datetime.now().strftime("%b %d, %Y %H:%M")}</sup>',
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 22, 'color': '#333'}
                },
                template='plotly_white',
                paper_bgcolor='#f8f9fa',
                plot_bgcolor='white'
            )
            
            fig.update_xaxes(showgrid=True, gridcolor='#e0e0e0')
            fig.update_yaxes(showgrid=True, gridcolor='#e0e0e0')
            
            # Save
            logger.info("Writing file...")
            fig.write_html(output_file, config={'displayModeBar': False})
            logger.info(f"✅ SUCCESS! Dashboard saved to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


if __name__ == "__main__":
    dashboard = ONAQualityDashboard('ona_data_export.csv')
    if dashboard.load_data():
        dashboard.generate_dashboard()
        print("\n✅ DONE! Open ona_dashboard.html to view")
