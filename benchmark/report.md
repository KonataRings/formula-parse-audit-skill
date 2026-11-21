# 自建基准报告

说明：本基准由本题作品自行构建，使用教科书公式，**不是**平台官方的三道隐藏案例，
其通过率不能当作官方得分。它检验的是一件事：同一公式经本 Skill 转换后算出的值，
是否与另一条独立写出的表达式一致。

| 案例 | 数值一致 | 符号齐全 | 相对误差 | 缺失符号 |
|-|-|-|-:|-|
| debye-lowT-heat-capacity | ✓ | ✓ | 0.00e+00 | - |
| ideal-gas-pressure | ✓ | ✓ | 0.00e+00 | - |
| arrhenius-rate | ✓ | ✓ | 0.00e+00 | - |
| einstein-heat-capacity | ✓ | ✓ | 0.00e+00 | - |
| debye-length | ✓ | ✓ | 0.00e+00 | - |
| fermi-energy | ✓ | ✓ | 0.00e+00 | - |
| larmor-frequency | ✓ | ✓ | 0.00e+00 | - |
| diffusion-length | ✓ | ✓ | 0.00e+00 | - |
| stefan-boltzmann-flux | ✓ | ✓ | 0.00e+00 | - |
| thermal-de-broglie | ✓ | ✓ | 0.00e+00 | - |

通过 **10/10**。

## 转换后的表达式

| 案例 | 表达式 |
|-|-|
| debye-lowT-heat-capacity | `((12)/(5))*pi**(4)*N*k_B*(((T)/(Theta)))**(3)` |
| ideal-gas-pressure | `((n*R*T)/(V))` |
| arrhenius-rate | `A*exp(-((E_a)/(R*T)))` |
| einstein-heat-capacity | `3*N*k_B*(((Theta)/(T)))**(2)*((exp(Theta/T))/((exp(Theta/T)-1)**(2)))` |
| debye-length | `sqrt(((epsilon_0*k_B*T)/(n*e**(2))))` |
| fermi-energy | `((hbar**(2))/(2*m))*(3*pi**(2)*n)**(2/3)` |
| larmor-frequency | `gamma*B` |
| diffusion-length | `sqrt(D*tau)` |
| stefan-boltzmann-flux | `sigma*T**(4)` |
| thermal-de-broglie | `((h)/(sqrt(2*pi*m*k_B*T)))` |
