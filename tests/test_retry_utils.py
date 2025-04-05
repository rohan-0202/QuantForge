import pytest
from unittest.mock import patch, Mock, call
import time

from db.retry_utils import retry_on_rate_limit


@pytest.mark.unit
class TestRetryUtils:
    """Test the retry_utils.py functionality."""

    def test_successful_execution_no_retry(self):
        """Test that a successful function execution doesn't trigger retries."""
        
        with patch('time.sleep') as mock_sleep:
            # Define a mock function that succeeds
            mock_func = Mock(return_value="success")
            
            # Apply the retry decorator
            decorated_func = retry_on_rate_limit()(mock_func)
            
            # Call the decorated function
            result = decorated_func()
            
            # Verify the function was called once and returned the expected result
            assert result == "success"
            mock_func.assert_called_once()
            mock_sleep.assert_not_called()  # sleep should not be called

    def test_retry_on_rate_limit(self):
        """Test that the function retries on rate limit errors."""
        
        with patch('time.sleep') as mock_sleep:
            # Define a mock function that fails with rate limit error twice, then succeeds
            mock_func = Mock(side_effect=[
                Exception("Too Many Requests"),  # First call - fail with rate limit
                Exception("Too Many Requests"),  # Second call - fail with rate limit
                "success"  # Third call - succeed
            ])
            
            # Apply the retry decorator
            decorated_func = retry_on_rate_limit(max_retries=3, base_delay=1)(mock_func)
            
            # Call the decorated function
            result = decorated_func()
            
            # Verify the function was called three times and returned the expected result
            assert result == "success"
            assert mock_func.call_count == 3
            
            # Verify sleep was called twice with increasing delays
            assert mock_sleep.call_count == 2
            
            # The first sleep should be around base_delay * 2^1 = 2 seconds (plus jitter)
            # The second sleep should be around base_delay * 2^2 = 4 seconds (plus jitter)
            # Since there's random jitter, we can only check that the values are in a reasonable range
            first_sleep = mock_sleep.call_args_list[0][0][0]
            second_sleep = mock_sleep.call_args_list[1][0][0]
            
            assert 1.9 <= first_sleep <= 5.0, f"First sleep value {first_sleep} not in expected range"
            assert 3.9 <= second_sleep <= 9.0, f"Second sleep value {second_sleep} not in expected range"

    def test_max_retries_exceeded(self):
        """Test that the function raises an exception after max retries."""
        
        with patch('time.sleep') as mock_sleep:
            # Define a mock function that always fails with rate limit error
            mock_func = Mock(side_effect=Exception("Too Many Requests"))
            
            # Apply the retry decorator with 2 max retries
            decorated_func = retry_on_rate_limit(max_retries=2, base_delay=1)(mock_func)
            
            # Call the decorated function and expect an exception
            with pytest.raises(Exception) as excinfo:
                decorated_func()
            
            # Verify the exception message
            assert "Too Many Requests" in str(excinfo.value)
            
            # Verify the function was called 3 times (initial + 2 retries)
            assert mock_func.call_count == 3
            
            # Verify sleep was called twice
            assert mock_sleep.call_count == 2

    def test_non_rate_limit_error(self):
        """Test that non-rate limit errors are not retried."""
        
        with patch('time.sleep') as mock_sleep:
            # Define a mock function that fails with a non-rate limit error
            mock_func = Mock(side_effect=ValueError("Some other error"))
            
            # Apply the retry decorator
            decorated_func = retry_on_rate_limit()(mock_func)
            
            # Call the decorated function and expect an exception
            with pytest.raises(ValueError) as excinfo:
                decorated_func()
            
            # Verify the exception message
            assert "Some other error" in str(excinfo.value)
            
            # Verify the function was called only once
            mock_func.assert_called_once()
            mock_sleep.assert_not_called()

    def test_backoff_calculation(self):
        """Test that backoff calculation works correctly with fixed jitter."""
        
        with patch('random.uniform', return_value=1.0) as mock_random:
            with patch('time.sleep') as mock_sleep:
                # Define a mock function that fails with rate limit errors multiple times
                mock_func = Mock(side_effect=[
                    Exception("Too Many Requests"),
                    Exception("Too Many Requests"),
                    Exception("Too Many Requests"),
                    "success"
                ])
                
                # Apply the retry decorator with specific base_delay
                decorated_func = retry_on_rate_limit(max_retries=3, base_delay=2)(mock_func)
                
                # Call the decorated function
                result = decorated_func()
                
                # Verify the function was called four times and returned the expected result
                assert result == "success"
                assert mock_func.call_count == 4
                
                # Verify sleep was called three times with the expected values
                # With jitter fixed at 1.0, the delays should be:
                # First retry: 2 * 2^1 + 1 = 5
                # Second retry: 2 * 2^2 + 1 = 9
                # Third retry: 2 * 2^3 + 1 = 17
                expected_calls = [call(5.0), call(9.0), call(17.0)]
                mock_sleep.assert_has_calls(expected_calls) 