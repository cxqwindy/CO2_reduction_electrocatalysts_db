"""
数据标签的config数据，表明字典对应
"""
# voltage == potential
# prompt_key: 想要从摘要里的得到的内容
prompt_key = ['materials', 'material type',
              'product', 'faraday efficiency', 'control method',
              'control method type', 'electrolyte',
              'current density', 'cell setup', 'potential']
# 标注结果映射表
# 1. 产物映射表
product_dict = ['CO', 'HCOOH', 'HCHO', 'CH4', 'CH3OH',
                'C2H4', 'C2H5OH', 'Acetone', 'C2+',
                'propanol', 'Syngas', 'C2H6', 'CH3COOH', 'CH3CHO']
# 2. 材料映射表,记得把Cu—》E
material_dict = ['C', 'E', 'E(Ox)-M(OH)x', 'E/C',
                 'ECLx', 'ECx', 'El', 'E-M',
                 'E-MOF', 'E-molecular complex', 'E-MOx', 'EMSx',
                 'E-MSx', 'E-MXene', 'ENx', 'EOx',
                 'EOx-MOx', 'EPx', 'ESex', 'ESx',
                 'POPs', 'ExCO3', 'EMOx']
material_mapping = {'M+EOx': 'E-MOx', 'E+MOx': 'E-MOx', 'COF': 'POPs', 'ECOF': 'POPs', 'MOF': 'E-MOF'}
# 3. 调控方法类别映射表
control_dict = ['defect', 'alloy', 'structure control', 'atomic level dispersion',
                'composite', 'surface/interface modification']
# 4. cell setup 映射表
cell_setup = ['H-type cell', 'Flow cell']