"""
ONA Data Quality Monitoring Dashboard
Automated dashboard to monitor key quality metrics from ONA data collection platform
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class ONAQualityDashboard:
    """
    Automated dashboard for monitoring data quality metrics from ONA platform
    """
    
    def __init__(self, data_path, config=None):
        """
        Initialize the dashboard with data and configuration
        
        Parameters:
        -----------
        data_path : str
            Path to the ONA exported data (CSV format)
        config : dict
            Configuration dictionary with thresholds and settings
        """
        self.data = pd.read_csv(data_path)
        
        # Default configuration (can be updated after pilot)
        self.config = config or {
            'min_duration': 30,  # minutes
            'max_duration': 120,  # minutes
            'target_districts': [],  # List of target districts
            'gps_tolerance': 0.01,  # GPS coordinate tolerance in degrees (~1km)
            'target_boundaries': None,  # Dict with 'lat_min', 'lat_max', 'lon_min', 'lon_max'
            'required_fields': [],  # List of required field names
            'logical_checks': []  # List of logical consistency rules
        }
        
        if config:
            self.config.update(config)
        
        self._prepare_data()
    
    def _prepare_data(self):
        """Prepare and clean the data for analysis"""
        # Convert submission time to datetime if exists
        time_columns = [col for col in self.data.columns if 'time' in col.lower() or 'date' in col.lower()]
        for col in time_columns:
            try:
                self.data[col] = pd.to_datetime(self.data[col])
            except:
                pass
        
        # Calculate interview duration if start and end times exist
        if 'start_time' in self.data.columns and 'end_time' in self.data.columns:
            self.data['duration_minutes'] = (
                (pd.to_datetime(self.data['end_time']) - 
                 pd.to_datetime(self.data['start_time']))
                .dt.total_seconds() / 60
            )
    
    def calculate_completion_rates(self, district_column='district'):
        """
        Calculate completion rates by district
        
        Parameters:
        -----------
        district_column : str
            Name of the column containing district information
        
        Returns:
        --------
        pd.DataFrame
            Completion rates by district
        """
        if district_column not in self.data.columns:
            print(f"Warning: '{district_column}' column not found")
            return pd.DataFrame()
        
        # Calculate total submissions by district
        district_counts = self.data[district_column].value_counts()
        
        # Calculate completed vs incomplete
        # Assuming a submission is complete if all required fields are filled
        if self.config['required_fields']:
            self.data['is_complete'] = self.data[self.config['required_fields']].notna().all(axis=1)
        else:
            # If no required fields specified, check overall completeness
            self.data['is_complete'] = self.data.notna().mean(axis=1) > 0.8
        
        completion_by_district = self.data.groupby(district_column).agg({
            'is_complete': ['sum', 'count', 'mean']
        }).round(4)
        
        completion_by_district.columns = ['completed', 'total', 'completion_rate']
        completion_by_district['completion_rate'] = (
            completion_by_district['completion_rate'] * 100
        ).round(2)
        
        return completion_by_district.reset_index()
    
    def analyze_missing_data(self):
        """
        Analyze patterns of missing data across all fields
        
        Returns:
        --------
        pd.DataFrame
            Missing data statistics by field
        """
        missing_data = pd.DataFrame({
            'field': self.data.columns,
            'missing_count': self.data.isna().sum().values,
            'missing_percentage': (self.data.isna().sum().values / len(self.data) * 100).round(2)
        })
        
        missing_data = missing_data[missing_data['missing_count'] > 0].sort_values(
            'missing_percentage', ascending=False
        )
        
        return missing_data
    
    def check_logical_inconsistencies(self, rules=None):
        """
        Check for logical inconsistencies in responses
        
        Parameters:
        -----------
        rules : list of dict
            List of logical rules to check. Each rule should have:
            - 'name': description of the rule
            - 'condition': lambda function or string condition
            - 'fields': list of fields involved
        
        Returns:
        --------
        pd.DataFrame
            Inconsistencies found
        """
        rules = rules or self.config['logical_checks']
        
        if not rules:
            # Default logical checks
            rules = []
        
        inconsistencies = []
        
        for rule in rules:
            try:
                if callable(rule['condition']):
                    violations = rule['condition'](self.data)
                else:
                    violations = self.data.eval(rule['condition'])
                
                violation_count = violations.sum() if isinstance(violations, pd.Series) else len(violations)
                
                inconsistencies.append({
                    'rule': rule['name'],
                    'violations': violation_count,
                    'percentage': (violation_count / len(self.data) * 100).round(2)
                })
            except Exception as e:
                print(f"Error checking rule '{rule['name']}': {str(e)}")
        
        return pd.DataFrame(inconsistencies)
    
    def flag_interview_durations(self, duration_column='duration_minutes'):
        """
        Flag interviews with suspicious durations
        
        Parameters:
        -----------
        duration_column : str
            Name of the column containing interview duration in minutes
        
        Returns:
        --------
        pd.DataFrame
            Flagged interviews
        """
        if duration_column not in self.data.columns:
            print(f"Warning: '{duration_column}' column not found")
            return pd.DataFrame()
        
        min_dur = self.config['min_duration']
        max_dur = self.config['max_duration']
        
        flagged = self.data[
            (self.data[duration_column] < min_dur) | 
            (self.data[duration_column] > max_dur)
        ].copy()
        
        flagged['flag_reason'] = flagged[duration_column].apply(
            lambda x: f'Too short (<{min_dur} min)' if x < min_dur else f'Too long (>{max_dur} min)'
        )
        
        return flagged
    
    def verify_gps_coordinates(self, lat_column='latitude', lon_column='longitude'):
        """
        Verify GPS coordinates are within target areas
        
        Parameters:
        -----------
        lat_column : str
            Name of the latitude column
        lon_column : str
            Name of the longitude column
        
        Returns:
        --------
        pd.DataFrame
            Records with GPS issues
        """
        if lat_column not in self.data.columns or lon_column not in self.data.columns:
            print(f"Warning: GPS columns not found")
            return pd.DataFrame()
        
        issues = []
        
        # Check for missing GPS
        missing_gps = self.data[
            self.data[lat_column].isna() | self.data[lon_column].isna()
        ].copy()
        
        if len(missing_gps) > 0:
            missing_gps['gps_issue'] = 'Missing GPS coordinates'
            issues.append(missing_gps)
        
        # Check for invalid coordinates (latitude: -90 to 90, longitude: -180 to 180)
        valid_data = self.data[
            self.data[lat_column].notna() & self.data[lon_column].notna()
        ]
        
        invalid_coords = valid_data[
            (valid_data[lat_column] < -90) | (valid_data[lat_column] > 90) |
            (valid_data[lon_column] < -180) | (valid_data[lon_column] > 180)
        ].copy()
        
        if len(invalid_coords) > 0:
            invalid_coords['gps_issue'] = 'Invalid GPS coordinates'
            issues.append(invalid_coords)
        
        # Check if coordinates are within target boundaries
        if self.config['target_boundaries']:
            bounds = self.config['target_boundaries']
            out_of_bounds = valid_data[
                (valid_data[lat_column] < bounds['lat_min']) |
                (valid_data[lat_column] > bounds['lat_max']) |
                (valid_data[lon_column] < bounds['lon_min']) |
                (valid_data[lon_column] > bounds['lon_max'])
            ].copy()
            
            if len(out_of_bounds) > 0:
                out_of_bounds['gps_issue'] = 'Outside target boundaries'
                issues.append(out_of_bounds)
        
        if issues:
            return pd.concat(issues, ignore_index=True)
        else:
            return pd.DataFrame()
    
    def generate_dashboard(self, output_file='ona_quality_dashboard.html', 
                          district_column='district',
                          duration_column='duration_minutes',
                          lat_column='latitude',
                          lon_column='longitude'):
        """
        Generate interactive HTML dashboard with all quality metrics
        
        Parameters:
        -----------
        output_file : str
            Output HTML file path
        district_column : str
            Name of district column
        duration_column : str
            Name of duration column
        lat_column : str
            Name of latitude column
        lon_column : str
            Name of longitude column
        """
        # Calculate all metrics
        completion_rates = self.calculate_completion_rates(district_column)
        missing_data = self.analyze_missing_data()
        duration_flags = self.flag_interview_durations(duration_column)
        gps_issues = self.verify_gps_coordinates(lat_column, lon_column)
        
        # Create subplots
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                'Completion Rates by District',
                'Interview Duration Distribution',
                'Top 10 Fields with Missing Data',
                'Daily Submission Trends',
                'GPS Coordinate Verification',
                'Data Quality Summary'
            ),
            specs=[
                [{"type": "bar"}, {"type": "histogram"}],
                [{"type": "bar"}, {"type": "scatter"}],
                [{"type": "scattermapbox"}, {"type": "table"}]
            ],
            row_heights=[0.33, 0.33, 0.34],
            vertical_spacing=0.12,
            horizontal_spacing=0.15
        )
        
        # 1. Completion rates by district
        if not completion_rates.empty:
            fig.add_trace(
                go.Bar(
                    x=completion_rates[district_column],
                    y=completion_rates['completion_rate'],
                    name='Completion Rate',
                    marker_color='#2E86AB',
                    text=completion_rates['completion_rate'].apply(lambda x: f'{x:.1f}%'),
                    textposition='outside'
                ),
                row=1, col=1
            )
        
        # 2. Interview duration distribution
        if duration_column in self.data.columns:
            fig.add_trace(
                go.Histogram(
                    x=self.data[duration_column].dropna(),
                    name='Duration',
                    marker_color='#A23B72',
                    nbinsx=30
                ),
                row=1, col=2
            )
            
            # Add vertical lines for thresholds
            fig.add_vline(
                x=self.config['min_duration'], 
                line_dash="dash", 
                line_color="red",
                annotation_text=f"Min: {self.config['min_duration']}",
                row=1, col=2
            )
            fig.add_vline(
                x=self.config['max_duration'], 
                line_dash="dash", 
                line_color="red",
                annotation_text=f"Max: {self.config['max_duration']}",
                row=1, col=2
            )
        
        # 3. Top 10 fields with missing data
        if not missing_data.empty:
            top_missing = missing_data.head(10)
            fig.add_trace(
                go.Bar(
                    y=top_missing['field'],
                    x=top_missing['missing_percentage'],
                    name='Missing %',
                    orientation='h',
                    marker_color='#F18F01',
                    text=top_missing['missing_percentage'].apply(lambda x: f'{x:.1f}%'),
                    textposition='outside'
                ),
                row=2, col=1
            )
        
        # 4. Daily submission trends
        if 'submission_time' in self.data.columns or any('date' in col.lower() for col in self.data.columns):
            # Find the date column
            date_col = 'submission_time' if 'submission_time' in self.data.columns else \
                       [col for col in self.data.columns if 'date' in col.lower()][0]
            
            daily_counts = self.data[date_col].dt.date.value_counts().sort_index()
            
            fig.add_trace(
                go.Scatter(
                    x=daily_counts.index,
                    y=daily_counts.values,
                    mode='lines+markers',
                    name='Submissions',
                    marker_color='#06A77D',
                    line=dict(width=2)
                ),
                row=2, col=2
            )
        
        # 5. GPS coordinate map
        if lat_column in self.data.columns and lon_column in self.data.columns:
            valid_gps = self.data[
                self.data[lat_column].notna() & self.data[lon_column].notna()
            ]
            
            if len(valid_gps) > 0:
                fig.add_trace(
                    go.Scattermapbox(
                        lat=valid_gps[lat_column],
                        lon=valid_gps[lon_column],
                        mode='markers',
                        marker=dict(size=8, color='#2E86AB'),
                        name='Interview Locations',
                        text=valid_gps.get(district_column, 'Location')
                    ),
                    row=3, col=1
                )
        
        # 6. Summary table
        summary_data = {
            'Metric': [
                'Total Submissions',
                'Completion Rate',
                'Records with Missing Data',
                'Duration Flags',
                'GPS Issues',
                'Data Collection Period'
            ],
            'Value': [
                f"{len(self.data):,}",
                f"{completion_rates['completion_rate'].mean():.1f}%" if not completion_rates.empty else 'N/A',
                f"{missing_data['missing_count'].sum():,.0f}" if not missing_data.empty else '0',
                f"{len(duration_flags):,}",
                f"{len(gps_issues):,}",
                f"{self.data['submission_time'].min().date()} to {self.data['submission_time'].max().date()}" 
                if 'submission_time' in self.data.columns else 'N/A'
            ]
        }
        
        fig.add_trace(
            go.Table(
                header=dict(
                    values=['<b>Metric</b>', '<b>Value</b>'],
                    fill_color='#2E86AB',
                    font=dict(color='white', size=12),
                    align='left'
                ),
                cells=dict(
                    values=[summary_data['Metric'], summary_data['Value']],
                    fill_color='#F0F0F0',
                    align='left',
                    font=dict(size=11)
                )
            ),
            row=3, col=2
        )
        
        # Update layout
        fig.update_layout(
            title={
                'text': 'ONA Data Quality Monitoring Dashboard',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 24, 'color': '#1a1a1a'}
            },
            showlegend=False,
            height=1400,
            template='plotly_white',
            font=dict(family="Arial, sans-serif")
        )
        
        # Update axes labels
        fig.update_xaxes(title_text="District", row=1, col=1)
        fig.update_yaxes(title_text="Completion Rate (%)", row=1, col=1)
        
        fig.update_xaxes(title_text="Duration (minutes)", row=1, col=2)
        fig.update_yaxes(title_text="Frequency", row=1, col=2)
        
        fig.update_xaxes(title_text="Missing Data (%)", row=2, col=1)
        fig.update_yaxes(title_text="Field Name", row=2, col=1)
        
        fig.update_xaxes(title_text="Date", row=2, col=2)
        fig.update_yaxes(title_text="Number of Submissions", row=2, col=2)
        
        # Update mapbox for GPS visualization
        fig.update_layout(
            mapbox=dict(
                style="open-street-map",
                center=dict(
                    lat=self.data[lat_column].mean() if lat_column in self.data.columns else 0,
                    lon=self.data[lon_column].mean() if lon_column in self.data.columns else 0
                ),
                zoom=8
            )
        )
        
        # Save dashboard
        fig.write_html(output_file)
        print(f"Dashboard saved to: {output_file}")
        
        return fig
    
    def export_quality_report(self, output_file='quality_report.xlsx',
                             district_column='district',
                             duration_column='duration_minutes',
                             lat_column='latitude',
                             lon_column='longitude'):
        """
        Export detailed quality report to Excel
        
        Parameters:
        -----------
        output_file : str
            Output Excel file path
        """
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Summary sheet
            completion_rates = self.calculate_completion_rates(district_column)
            completion_rates.to_excel(writer, sheet_name='Completion Rates', index=False)
            
            # Missing data sheet
            missing_data = self.analyze_missing_data()
            missing_data.to_excel(writer, sheet_name='Missing Data', index=False)
            
            # Duration flags sheet
            duration_flags = self.flag_interview_durations(duration_column)
            if not duration_flags.empty:
                duration_flags.to_excel(writer, sheet_name='Duration Flags', index=False)
            
            # GPS issues sheet
            gps_issues = self.verify_gps_coordinates(lat_column, lon_column)
            if not gps_issues.empty:
                gps_issues.to_excel(writer, sheet_name='GPS Issues', index=False)
        
        print(f"Quality report exported to: {output_file}")


def main():
    """
    Example usage of the ONA Quality Dashboard
    """
    # Configuration
    config = {
        'min_duration': 30,  # Update after pilot
        'max_duration': 120,  # Update after pilot
        'required_fields': ['respondent_name', 'district', 'survey_complete'],
        'target_boundaries': {
            'lat_min': -5.0,
            'lat_max': 5.0,
            'lon_min': 29.0,
            'lon_max': 35.0
        },
        'logical_checks': [
            {
                'name': 'Age consistency',
                'condition': lambda df: (df.get('age', 0) < 0) | (df.get('age', 0) > 120),
                'fields': ['age']
            }
        ]
    }
    
    # Initialize dashboard
    print("Initializing ONA Quality Dashboard...")
    dashboard = ONAQualityDashboard('ona_data_export.csv', config=config)
    
    # Generate dashboard
    print("Generating dashboard...")
    dashboard.generate_dashboard(
        output_file='ona_quality_dashboard.html',
        district_column='district',
        duration_column='duration_minutes',
        lat_column='latitude',
        lon_column='longitude'
    )
    
    # Export quality report
    print("Exporting quality report...")
    dashboard.export_quality_report('quality_report.xlsx')
    
    print("Dashboard generation complete!")


if __name__ == "__main__":
    main()
