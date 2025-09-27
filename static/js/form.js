// 多页表单逻辑
function nextStep(step) {
    // 校验当前页必填项
    let valid = true;
    let msg = '';
    let data = {};
    let currentStep = step - 1;
    if (step === 2) {
        // 第1页校验
        let name = document.getElementById('name').value.trim();
        let gender = document.getElementById('gender').value;
        let age = document.getElementById('age').value.trim();
        let contact = document.getElementById('contact').value.trim();
        // 联系方式必须为11位数字
        if (!name) valid = false;
        if (!gender) valid = false;
        if (!/^\d{11}$/.test(contact)) {
            valid = false;
            msg = '联系方式必须为11位数字';
        }
        // 年龄区间限制
        if (age) {
            let ageNum = parseInt(age);
            if (isNaN(ageNum) || ageNum < 10 || ageNum > 120) {
                valid = false;
                msg = '年龄必须在10-120之间';
            }
        }
        if (!valid && !msg) msg = '请填写完整第1页所有必填项';
        data = {step: 1, name, gender, age, contact};
    } else if (step === 3) {
        // 第2页校验
        let location = document.getElementById('location').value.trim();
        let industry = document.getElementById('industry').value.trim();
        let job_role = document.getElementById('job_role').value.trim();
        if (!industry) valid = false;
        if (!job_role) valid = false;
        if (!valid) msg = '请填写完整第2页所有必填项';
        data = {step: 2, location, industry, job_role};
    } else if (step === 4) {
        // 第3页校验
        let preference_type = document.getElementById('preference_type').value;
        let investment_preference = document.getElementById('investment_preference').value.trim();
        let incubation_info = document.getElementById('incubation_info').value.trim();
        let investment_experience = document.getElementById('investment_experience').value.trim();
        let tech_adaptability = document.getElementById('tech_adaptability').value.trim();
        if (!preference_type) valid = false;
        if (!valid) msg = '请填写完整第3页所有必填项';
        data = {step: 3, preference_type, investment_preference, incubation_info, investment_experience, tech_adaptability};
    }
    if (!valid) {
        showStepMsg(msg);
        return;
    }
    hideStepMsg();
    // AJAX提交本页数据
    if (step <= 4) {
        fetch('/submit_step', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        }).then(res => res.json()).then(resp => {
            if (resp.success) {
                for (let i = 1; i <= 4; i++) {
                    document.getElementById('step-' + i).style.display = (i === step) ? 'block' : 'none';
                }
                // 最后一步跳转
                if (resp.redirect) {
                    window.location.href = resp.redirect;
                }
            } else {
                showStepMsg(resp.msg || '提交失败，请重试');
            }
        }).catch(() => {
            showStepMsg('网络错误，请重试');
        });
    }
}

// 显示每页校验提示
function showStepMsg(msg) {
    let msgDiv = document.getElementById('step-msg');
    if (!msgDiv) {
        msgDiv = document.createElement('div');
        msgDiv.id = 'step-msg';
        msgDiv.className = 'msg';
        document.querySelector('.form-page').insertBefore(msgDiv, document.querySelector('.form-page').children[1]);
    }
    msgDiv.innerText = msg;
}
function hideStepMsg() {
    let msgDiv = document.getElementById('step-msg');
    if (msgDiv) msgDiv.innerText = '';
}

// 投资偏好类型联动（原有条件显示逻辑）
function togglePreferenceFields() {
    const preferenceType = document.getElementById('preference_type').value;
    const investmentFields = document.getElementById('investment_preference_group');
    const incubationFields = document.getElementById('incubation_info_group');
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
    // 投资偏好类型联动
    const preferenceSelect = document.getElementById('preference_type');
    if (preferenceSelect) {
        preferenceSelect.addEventListener('change', function() {
            togglePreferenceFields();
        });
        // 初始化状态
        togglePreferenceFields();
    }
});