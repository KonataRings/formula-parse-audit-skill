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

## 结构还原（MathML → LaTeX）

| 案例 | 一致 | 取得方式 | LaTeX | 期望 | 说明 |
|-|-|-|-|-|-|
| mass-energy | ✓ | reconstructed | `E=m{c}^{2}` | `E=m{c}^{2}` | superscript on a single letter |
| invisible-times | ✓ | reconstructed | `2\pi m{k}^{2}` | `2\pi m{k}^{2}` | U+2062 must vanish, not become an operator |
| function-application | ✓ | reconstructed | `\mathrm{sin}(x)` | `\mathrm{sin}(x)` | U+2061 is function application; sin(x) is not sin*(x) |
| root-of-fraction | ✓ | reconstructed | `\omega=\sqrt{\frac{k}{m}}` | `\omega=\sqrt{\frac{k}{m}}` | square root wrapping a fraction |
| subscript-superscript | ✓ | reconstructed | `{x}_{i}^{2}+{x}_{j}^{2}` | `{x}_{i}^{2}+{x}_{j}^{2}` | msubsup keeps both scripts on the same base |
| piecewise | ✓ | reconstructed | `f(x)=\begin{cases}x & x>0 \\ -x & x\le0\end{cases}` | `f(x)=\begin{cases}x & x>0 \\ -x & x\le 0\end{cases}` | braced table becomes cases; rows are two columns |
| uppercase-greek | ✓ | reconstructed | `\Theta=\frac{h{\nu}_{D}}{{k}_{B}}` | `\Theta=\frac{h{\nu}_{D}}{{k}_{B}}` | uppercase Greek and two subscripted factors |
| alttext-only | ✓ | reconstructed | `a+b` | `a+b` | when the publisher gives alttext LaTeX, prefer it over reconstruction |

结构还原通过 **8/8**（比较前统一空格、括号与 `\dfrac`/`\frac` 差异）。

## 汇总

- 数值核对：**10/10**
- 结构还原：**8/8**
