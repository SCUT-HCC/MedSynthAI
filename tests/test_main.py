import pytest
from unittest.mock import patch, MagicMock
from research.main import (
    BatchProcessor,
    setup_logging,
    parse_arguments,
    is_case_completed,
    load_dataset,
    process_single_sample,
    run_workflow_batch,
    generate_summary_report,
    main
)
import logging.config

# 测试 BatchProcessor 类
def test_batch_processor_initialization():
    processor = BatchProcessor(num_threads=10)
    assert processor.num_threads == 10
    assert processor.processed_count == 0
    assert processor.success_count == 0
    assert processor.failed_count == 0
    assert processor.skipped_count == 0
    assert processor.results == []
    assert processor.failed_samples == []

def test_batch_processor_update_progress():
    processor = BatchProcessor()
    processor.update_progress(success=True, result={"sample_index": 1})
    assert processor.processed_count == 1
    assert processor.success_count == 1
    assert processor.results == [{"sample_index": 1}]
    
    processor.update_progress(success=False, error=Exception("Test Error"), sample_index=2)
    assert processor.processed_count == 2
    assert processor.failed_count == 1
    assert processor.failed_samples == [{'sample_index': 2, 'error': 'Test Error', 'timestamp': processor.failed_samples[0]['timestamp']}]

def test_batch_processor_update_skipped():
    processor = BatchProcessor()
    processor.update_skipped(sample_index=1)
    assert processor.processed_count == 0
    assert processor.skipped_count == 1

def test_batch_processor_get_progress_stats():
    processor = BatchProcessor()
    processor.update_progress(success=True, result={"sample_index": 1})
    processor.update_progress(success=False, error=Exception("Test Error"), sample_index=2)
    processor.update_skipped(sample_index=3)
    stats = processor.get_progress_stats()
    assert stats['processed'] == 2
    assert stats['success'] == 1
    assert stats['failed'] == 1
    assert stats['skipped'] == 1
    assert stats['success_rate'] == 0.5

# 测试 setup_logging 函数
@patch('os.makedirs')
@patch('logging.basicConfig')
def test_setup_logging(mock_basicConfig, mock_makedirs):
    setup_logging(log_dir='test_logs', log_level='DEBUG')
    mock_makedirs.assert_called_once_with('test_logs', exist_ok=True)
    mock_basicConfig.assert_called_once_with(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('test_logs/batch_processing_*.log', encoding='utf-8')
        ]
    )

# 测试 parse_arguments 函数
def test_parse_arguments():
    with patch('sys.argv', ['research/main.py', '--num-threads', '5']):
        args = parse_arguments()
        assert args.num_threads == 5

# 测试 is_case_completed 函数
@patch('glob.glob', return_value=['test_logs/workflow_1_case_0001.jsonl'])
@patch('os.remove')
@patch('json.loads', return_value={'event_type': 'workflow_complete'})
def test_is_case_completed(mock_json_loads, mock_os_remove, mock_glob):
    assert is_case_completed('test_logs', 1) == True
    mock_glob.assert_called_once_with('test_logs/workflow_*_case_0001.jsonl')
    mock_json_loads.assert_called_once()
    mock_os_remove.assert_not_called()

# 测试 load_dataset 函数
@patch('os.path.exists', return_value=True)
@patch('json.load', return_value=[{'病案介绍': 'Test Case 1'}, {'病案介绍': 'Test Case 2'}])
def test_load_dataset(mock_json_load, mock_os_exists):
    dataset = load_dataset('test_data.json', start_index=0, end_index=2)
    assert len(dataset) == 2
    assert dataset[0]['病案介绍'] == 'Test Case 1'
    assert dataset[1]['病案介绍'] == 'Test Case 2'

# 测试 process_single_sample 函数
@patch('research.main.MedicalWorkflow')
def test_process_single_sample(mock_MedicalWorkflow):
    args = parse_arguments()
    processor = BatchProcessor()
    sample_data = {'病案介绍': 'Test Case'}
    mock_instance = mock_MedicalWorkflow.return_value
    mock_instance.run.return_value = 'test_logs/workflow_1_case_0001.jsonl'
    mock_instance.get_current_status.return_value = {'current_step': 5, 'workflow_success': True}
    mock_instance.get_medical_summary.return_value = 'Test Summary'
    
    result = process_single_sample(sample_data, 1, args, processor)
    assert result['sample_index'] == 1
    assert result['workflow_status']['current_step'] == 5
    assert result['medical_summary'] == 'Test Summary'

# 测试 run_workflow_batch 函数
@patch('research.main.ThreadPoolExecutor')
@patch('research.main.process_single_sample')
@patch('research.main.BatchProcessor')
def test_run_workflow_batch(mock_BatchProcessor, mock_process_single_sample, mock_ThreadPoolExecutor):
    args = parse_arguments()
    dataset = [{'病案介绍': 'Test Case 1'}, {'病案介绍': 'Test Case 2'}]
    mock_processor = mock_BatchProcessor.return_value
    mock_processor.get_progress_stats.return_value = {
        'processed': 2,
        'success': 2,
        'failed': 0,
        'skipped': 0,
        'success_rate': 1.0,
        'elapsed_time': 1.0,
        'samples_per_minute': 120.0
    }
    mock_future = MagicMock()
    mock_future.result.return_value = None
    mock_ThreadPoolExecutor.return_value.__enter__.return_value.submit.return_value = mock_future
    
    batch_results = run_workflow_batch(dataset, args)
    assert batch_results['summary']['total_samples'] == 2
    assert batch_results['summary']['successful_samples'] == 2

# 测试 generate_summary_report 函数
@patch('json.dump')
@patch('os.makedirs')
def test_generate_summary_report(mock_os_makedirs, mock_json_dump):
    batch_results = {
        'summary': {
            'total_samples': 2,
            'processed_samples': 2,
            'successful_samples': 2,
            'failed_samples': 0,
            'skipped_samples': 0,
            'success_rate': 1.0,
            'total_execution_time': 1.0,
            'average_time_per_sample': 0.5,
            'samples_per_minute': 120.0,
            'failed_sample_details': [],
            'processing_config': {
                'num_threads': 1,
                'model_type': 'deepseek-v3',
                'max_steps': 30,
                'dataset_range': '[0, 2)'
            }
        },
        'results': []
    }
    generate_summary_report(batch_results, 'test_output')
    mock_os_makedirs.assert_called_once_with('test_output', exist_ok=True)
    mock_json_dump.assert_called_once()

# 测试 main 函数
@patch('research.main.setup_logging')
@patch('research.main.parse_arguments')
@patch('research.main.load_dataset')
@patch('research.main.run_workflow_batch')
@patch('research.main.generate_summary_report')
def test_main(mock_generate_summary_report, mock_run_workflow_batch, mock_load_dataset, mock_parse_arguments, mock_setup_logging):
    args = parse_arguments()
    mock_parse_arguments.return_value = args
    mock_load_dataset.return_value = [{'病案介绍': 'Test Case'}]
    mock_run_workflow_batch.return_value = {
        'summary': {
            'total_samples': 1,
            'processed_samples': 1,
            'successful_samples': 1,
            'failed_samples': 0,
            'skipped_samples': 0,
            'success_rate': 1.0,
            'total_execution_time': 1.0,
            'average_time_per_sample': 1.0,
            'samples_per_minute': 60.0,
            'failed_sample_details': [],
            'processing_config': {
                'num_threads': 1,
                'model_type': 'deepseek-v3',
                'max_steps': 30,
                'dataset_range': '[0, 1)'
            }
        },
        'results': []
    }
    main()
    mock_setup_logging.assert_called_once_with(args.batch_log_dir, args.log_level)
    mock_load_dataset.assert_called_once_with(args.dataset_path, args.start_index, args.end_index, args.sample_limit)
    mock_run_workflow_batch.assert_called_once_with([{'病案介绍': 'Test Case'}], args)
    mock_generate_summary_report.assert_called_once_with(mock_run_workflow_batch.return_value, args.output_dir)

# 测试 .env 文件加载
@patch('research.main.os.path.exists', return_value=True)
@patch('research.main.open', new_callable=MagicMock)
@patch('research.main.dotenv.load_dotenv')
@patch('research.main.os.getenv', return_value='your_api_key_here')
def test_env_file_loading(mock_os_getenv, mock_load_dotenv, mock_open, mock_exists):
    mock_open.return_value.__enter__.return_value.read.return_value = 'API_KEY=your_api_key_here'
    mock_load_dotenv.return_value = None
    
    # 调用 parse_arguments 并验证 API_KEY 是否被正确加载
    args = parse_arguments()
    assert args.api_key == 'your_api_key_here'

# 测试 .gitignore 文件的更新
def test_gitignore_updates():
    with open('.gitignore', 'r') as f:
        gitignore_content = f.read()
    assert 'results_11_15testneike/' in gitignore_content
    assert 'results/' in gitignore_content
    assert '.env' in gitignore_content

# 测试 动态指导更新逻辑
@patch('research.main.GuidanceLoader')
def test_dynamic_guidance(mock_GuidanceLoader):
    args = parse_arguments()
    args.use_inquiry_guidance = True
    args.use_dynamic_guidance = True
    args.department_filter = None
    args.max_steps = 2
    
    processor = BatchProcessor()
    sample_data = {'病案介绍': 'Test Case'}
    mock_instance = mock_GuidanceLoader.return_value
    mock_instance.load_inquiry_guidance.return_value = {}

    process_single_sample(sample_data, 1, args, processor)
    mock_GuidanceLoader.assert_called_once_with(
        department_guidance="",
        use_dynamic_guidance=True,
        use_department_comparison=True,
        department_guidance_file=args.department_guidance_file,
        comparison_rules_file=args.comparison_rules_file
    )
    mock_instance.load_inquiry_guidance.assert_called_once_with(None)

# 测试 日志记录配置
def test_logging_configuration():
    import research.main
    research.main.setup_logging(log_dir='test_logs', log_level='DEBUG')
    logger = logging.getLogger()
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 2
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    assert isinstance(logger.handlers[1], logging.FileHandler)
    assert logger.handlers[1].baseFilename.endswith('test_logs/batch_processing_*.log')

# 测试 分诊代理和响应模型的支持
@patch('research.main.MedicalWorkflow')
def test_triage_support(mock_MedicalWorkflow):
    args = parse_arguments()
    args.use_inquiry_guidance = True
    args.use_dynamic_guidance = True
    args.department_filter = None
    args.max_steps = 2
    
    processor = BatchProcessor()
    sample_data = {'病案介绍': 'Test Case'}
    mock_instance = mock_MedicalWorkflow.return_value
    mock_instance.run.return_value = 'test_logs/workflow_1_case_0001.jsonl'
    mock_instance.get_current_status.return_value = {'current_step': 5, 'workflow_success': True}
    mock_instance.get_medical_summary.return_value = 'Test Summary'
    
    process_single_sample(sample_data, 1, args, processor)
    mock_GuidanceLoader.assert_called_once_with(
        department_guidance="",
        use_dynamic_guidance=True,
        use_department_comparison=True,
        department_guidance_file=args.department_guidance_file,
        comparison_rules_file=args.comparison_rules_file
    )
    mock_instance.load_inquiry_guidance.assert_called_once_with(None)
