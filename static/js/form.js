// 表单条件显示逻辑
function togglePreferenceFields() {
    const preferenceType = document.getElementById('preference_type').value;
    const investmentFields = document.getElementById('investment_fields');
    const incubationFields = document.getElementById('incubation_fields');
    
    if (preferenceType === 'RWA投资') {
        investmentFields.style.display = 'block';
        incubationFields.style.display = 'none';
        document.querySelector('textarea[name="investment_preference"]').required = true;
        document.querySelector('textarea[name="incubation_info"]').required = false;
    } else if (preferenceType === 'RWA孵化') {
        investmentFields.style.display = 'none';
        incubationFields.style.display = 'block';
        document.querySelector('textarea[name="investment_preference"]').required = false;
        document.querySelector('textarea[name="incubation_info"]').required = true;
    } else {
        investmentFields.style.display = 'none';
        incubationFields.style.display = 'none';
        document.querySelector('textarea[name="investment_preference"]').required = false;
        document.querySelector('textarea[name="incubation_info"]').required = false;
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 如果有偏好选择下拉框，添加事件监听器
    const preferenceSelect = document.getElementById('preference_type');
    if (preferenceSelect) {
        preferenceSelect.addEventListener('change', togglePreferenceFields);
        // 初始化状态
        togglePreferenceFields();
    }
});